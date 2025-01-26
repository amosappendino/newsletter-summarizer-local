from fastapi import APIRouter, Query, HTTPException
import psycopg2
import os
from dotenv import load_dotenv
import openai
import json
from fastapi.responses import RedirectResponse
from app.services.gmail_service import (
    authenticate_gmail,
    list_labels,
    search_messages,
    is_authenticated
)
import base64
from app.services.openai_service import get_summary

# Load environment variables
load_dotenv()

# Database connection config
DB_CONFIG = {
    'dbname': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT'),
}

# OpenAI API Key
openai.api_key = os.getenv('OPENAI_API_KEY')

router = APIRouter()

@router.get("/")
def read_root():
    return {"message": "Hello from API"}

def get_email_list(query):
    """Fetch email metadata (id, sender, subject) based on sender or subject query."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT id, sender, subject, received_at FROM emails WHERE sender ILIKE %s OR subject ILIKE %s",
                    (f'%{query}%', f'%{query}%'))
        emails = cur.fetchall()
        cur.close()
        conn.close()
        return [{"id": row[0], "sender": row[1], "subject": row[2], "received_at": row[3]} for row in emails]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def get_email_content(email_id):
    """Fetch the content of a specific email by ID."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT body FROM emails WHERE id = %s", (email_id,))
        email_body = cur.fetchone()
        cur.close()
        conn.close()
        if email_body:
            return email_body[0]
        else:
            raise HTTPException(status_code=404, detail="Email not found.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def summarize_content(email_body):
    """Use OpenAI to summarize a single email."""
    try:
        print(f"Starting summarization. Email body length: {len(email_body)}")
        
        # Truncate email body to roughly 500 tokens ≈ 2000 characters
        max_chars = 2000
        if len(email_body) > max_chars:
            print(f"Email body too long ({len(email_body)} chars), truncating to {max_chars} chars")
            email_body = email_body[:max_chars] + "..."

        prompt = f"Provide a brief summary of the key points from this email:\n{email_body}"
        
        print("Making OpenAI API call...")
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Create a concise summary focusing only on the most important points."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,  # Reduced output tokens
            temperature=0.5  # Lower temperature for more focused summaries
        )
        
        summary = response['choices'][0]['message']['content']

        # Extract token usage info from API response
        token_usage = response.get('usage', {})
        input_tokens = token_usage.get('prompt_tokens', 0)
        output_tokens = token_usage.get('completion_tokens', 0)
        total_tokens = token_usage.get('total_tokens', 0)

        # Cost estimation
        cost_per_1k_input = 0.0005   # GPT-3.5-turbo input cost
        cost_per_1k_output = 0.0015  # GPT-3.5-turbo output cost
        input_cost = (input_tokens / 1000) * cost_per_1k_input
        output_cost = (output_tokens / 1000) * cost_per_1k_output
        total_cost = input_cost + output_cost

        print(f"Tokens used - Input: {input_tokens}, Output: {output_tokens}, Total: {total_tokens}")
        print(f"Estimated Cost: ${total_cost:.6f}")

        return summary
    except Exception as e:
        print(f"Error during summarization: {str(e)}")
        raise Exception(f"Summarization failed: {str(e)}")

@router.get("/search-emails/")
async def search_emails(query: str = Query(..., description="Search query for emails")):
    """Search emails by sender or subject."""
    try:
        print(f"Starting search with query: {query}")  # Debug log
        
        # Get Gmail service
        try:
            service = authenticate_gmail()
            print("Gmail authentication successful")
        except Exception as e:
            print(f"Authentication error: {str(e)}")
            raise HTTPException(status_code=401, detail="Gmail authentication failed")
        
        # Get folder ID
        try:
            folder_id = list_labels(service)
            print(f"Folder ID: {folder_id}")  # Debug log
            if not folder_id:
                print("Folder not found")
                return []
        except Exception as e:
            print(f"Error getting folder ID: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to access Gmail folder")

        # Search for emails
        try:
            print("Starting message search...")  # Debug log
            results = search_messages(service, query, folder_id)
            print(f"Raw search results: {results}")  # Debug log
        except Exception as e:
            print(f"Search error: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to search messages")

        if not results:
            print("No results found")
            return []
            
        # Format results
        try:
            emails = []
            for msg in results:
                email = {
                    'id': msg.get('id'),
                    'sender': msg.get('sender', 'Unknown'),
                    'subject': msg.get('subject', 'No subject')
                }
                emails.append(email)
            print(f"Successfully formatted {len(emails)} emails")
            return emails
        except Exception as e:
            print(f"Error formatting results: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to format email results")
        
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Unexpected error in search_emails: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/summarize-email/")
async def summarize_email(email_id: str):
    """Summarize the content of a specific email."""
    try:
        # Get Gmail service
        service = authenticate_gmail()
        
        # Get the full email content
        message = service.users().messages().get(
            userId='me',
            id=email_id,
            format='full'
        ).execute()

        # Extract headers
        headers = message.get('payload', {}).get('headers', [])
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No subject')
        
        # Extract body content
        body = ""
        if 'parts' in message.get('payload', {}):
            for part in message['payload']['parts']:
                if part.get('mimeType') == 'text/plain':
                    body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                    break
        elif 'body' in message.get('payload', {}):
            if 'data' in message['payload']['body']:
                body = base64.urlsafe_b64decode(message['payload']['body']['data']).decode('utf-8')

        if not body:
            raise HTTPException(status_code=400, detail="No email content found to summarize")

        # Get summary from OpenAI
        summary = await get_summary(subject, body)
        return {"summary": summary}

    except Exception as e:
        print(f"Error in summarize_email: {str(e)}")  # Debug log
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/logout")
async def logout_route():
    try:
        from app.services.gmail_service import logout
        result = logout()
        if not result:  # If somehow result is None
            return {"message": "Logout completed but no status returned"}
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/auth/gmail")
async def gmail_auth():
    """Initiate Gmail authentication flow."""
    try:
        from app.services.gmail_service import authenticate_gmail
        service = authenticate_gmail()
        if service:
            # First check if setup is completed
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'folder_config.json')
            if os.path.exists(config_path):
                # If setup is done, redirect to main page
                return RedirectResponse(url="http://localhost:3000")
            else:
                # If setup is not done, redirect to setup page
                return RedirectResponse(url="http://localhost:3000/setup")
        raise HTTPException(status_code=401, detail="Authentication failed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/check-auth")
async def check_auth():
    """Check if user is authenticated with Gmail."""
    try:
        from app.services.gmail_service import is_authenticated
        if is_authenticated():
            return {"status": "authenticated"}
        return {"status": "unauthenticated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/check-email/{email_id}")
async def check_email(email_id: int):
    """Check if an email exists and return its metadata."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("""
            SELECT id, sender, subject, received_at 
            FROM emails 
            WHERE id = %s
        """, (email_id,))
        email = cur.fetchone()
        cur.close()
        conn.close()
        
        if email:
            return {
                "exists": True,
                "email": {
                    "id": email[0],
                    "sender": email[1],
                    "subject": email[2],
                    "received_at": email[3]
                }
            }
        return {"exists": False, "message": f"No email found with ID {email_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/setup-folder")
async def setup_folder(folder_data: dict):
    """Save the user's newsletter folder name."""
    try:
        folder_name = folder_data.get('folder_name')
        if not folder_name:
            raise HTTPException(status_code=400, detail="Folder name is required")
        
        # Create config directory if it doesn't exist
        config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config')
        os.makedirs(config_dir, exist_ok=True)
        
        # Save folder name to config file
        config_path = os.path.join(config_dir, 'folder_config.json')
        with open(config_path, 'w') as f:
            json.dump({'folder_name': folder_name}, f)
        
        return {"message": "Folder setup complete"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/check-setup")
async def check_setup():
    """Check if the folder setup has been completed."""
    try:
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'folder_config.json')
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
                return {"is_setup": bool(config.get('folder_name'))}
        return {"is_setup": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
