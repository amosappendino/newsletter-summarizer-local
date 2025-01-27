from fastapi import APIRouter, Query, HTTPException, Depends, Request
import psycopg2
import os
from dotenv import load_dotenv
import openai
import json
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from app.services.gmail_service import (
    authenticate_gmail,
    list_labels,
    search_messages,
    is_authenticated
)
import base64
from app.services.openai_service import get_summary
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
import google.auth.transport.requests
from datetime import datetime
from googleapiclient.discovery import build

# Load environment variables
load_dotenv()

# Database connection config
DB_CONFIG = {
    'dbname': os.getenv('POSTGRES_DB'),
    'user': os.getenv('POSTGRES_USER'),
    'password': os.getenv('POSTGRES_PASSWORD'),
    'host': os.getenv('POSTGRES_HOST'),
    'port': os.getenv('POSTGRES_PORT')
}

# OpenAI API Key
openai.api_key = os.getenv('OPENAI_API_KEY')

router = APIRouter()

# Store states temporarily (in production, use a proper session/database)
active_states = set()

def clear_token():
    """Clear stored token file if it exists"""
    try:
        if os.path.exists('token.json'):
            os.remove('token.json')
            print("Token file removed successfully")
    except Exception as e:
        print(f"Error removing token file: {str(e)}")

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
    """Search emails by sender, subject, or body content"""
    try:
        print(f"Starting search with query: '{query}'")
        
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Make query case-insensitive
        search_term = f"%{query}%"
        
        # First search in sender and subject (priority matches)
        cur.execute("""
            SELECT id, sender, subject, body, received_at
            FROM emails 
            WHERE 
                LOWER(sender) LIKE LOWER(%s) OR 
                LOWER(subject) LIKE LOWER(%s)
            UNION
            -- Then search in body (secondary matches)
            SELECT id, sender, subject, body, received_at
            FROM emails 
            WHERE 
                LOWER(body) LIKE LOWER(%s) AND
                id NOT IN (
                    SELECT id FROM emails 
                    WHERE LOWER(sender) LIKE LOWER(%s) OR 
                          LOWER(subject) LIKE LOWER(%s)
                )
            ORDER BY received_at DESC
        """, (search_term, search_term, search_term, search_term, search_term))
        
        results = cur.fetchall()
        print(f"Found {len(results)} matching emails")
        
        emails = []
        for row in results:
            email = {
                "id": row[0],
                "sender": row[1],
                "subject": row[2],
                "preview": row[3][:200] + "..." if row[3] and len(row[3]) > 200 else row[3],
                "received_at": row[4].isoformat() if row[4] else None,
                "match_type": "sender/subject" if (
                    query.lower() in row[1].lower() or 
                    query.lower() in row[2].lower()
                ) else "body"
            }
            emails.append(email)
            print(f"Match found - Subject: {row[2]}, Sender: {row[1]}")
        
        cur.close()
        conn.close()
        
        return JSONResponse({
            "status": "success",
            "query": query,
            "count": len(emails),
            "results": emails
        })
            
    except Exception as e:
        print(f"Error in search_emails: {str(e)}")
        return JSONResponse({
            "status": "error",
            "message": str(e)
        })

# Add a new endpoint to search with more details
@router.get("/detailed-search/")
async def detailed_search(query: str = Query(..., description="Search query for emails")):
    """Detailed search with debugging information"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # First, get some sample data to verify what we're searching through
        cur.execute("""
            SELECT COUNT(*) total_emails,
                   COUNT(DISTINCT sender) unique_senders,
                   MIN(received_at) earliest_email,
                   MAX(received_at) latest_email
            FROM emails
        """)
        stats = cur.fetchone()
        
        # Then do the search
        search_term = f"%{query}%"
        cur.execute("""
            SELECT id, sender, subject, 
                   LEFT(body, 200) as preview,
                   received_at
            FROM emails 
            WHERE 
                LOWER(sender) LIKE LOWER(%s) OR 
                LOWER(subject) LIKE LOWER(%s) OR 
                LOWER(body) LIKE LOWER(%s)
            ORDER BY received_at DESC
        """, (search_term, search_term, search_term))
        
        results = cur.fetchall()
        
        emails = [{
            "id": row[0],
            "sender": row[1],
            "subject": row[2],
            "preview": row[3],
            "received_at": row[4].isoformat() if row[4] else None
        } for row in results]
        
        cur.close()
        conn.close()
        
        return JSONResponse({
            "status": "success",
            "query_info": {
                "search_term": query,
                "search_pattern": search_term
            },
            "database_stats": {
                "total_emails": stats[0],
                "unique_senders": stats[1],
                "date_range": {
                    "earliest": stats[2].isoformat() if stats[2] else None,
                    "latest": stats[3].isoformat() if stats[3] else None
                }
            },
            "results": {
                "count": len(emails),
                "emails": emails
            }
        })
            
    except Exception as e:
        print(f"Error in detailed_search: {str(e)}")
        return JSONResponse({
            "status": "error",
            "message": str(e)
        })

@router.get("/summarize-email/")
async def summarize_email(email_id: int):
    """Generate a summary for a specific email"""
    try:
        # Connect to database
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Get email content
        cur.execute("""
            SELECT subject, body 
            FROM emails 
            WHERE id = %s
        """, (email_id,))
        
        result = cur.fetchone()
        if not result:
            return JSONResponse({
                "status": "error",
                "message": "Email not found"
            })
            
        subject, body = result
        
        # Generate summary using OpenAI
        summary = await get_summary(subject, body)
        
        cur.close()
        conn.close()
        
        return JSONResponse({
            "status": "success",
            "summary": summary
        })
        
    except Exception as e:
        print(f"Error generating summary: {str(e)}")
        return JSONResponse({
            "status": "error",
            "message": str(e)
        }, status_code=500)

@router.get("/logout", response_model=None)
async def logout():
    """Clear token and log out user"""
    try:
        clear_token()
        return JSONResponse({
            "status": "success",
            "message": "Logged out successfully"
        })
    except Exception as e:
        print(f"Error during logout: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def refresh_token(credentials: Credentials) -> bool:
    """Refresh the token if possible"""
    try:
        if credentials and credentials.expired and credentials.refresh_token:
            request = google.auth.transport.requests.Request()
            credentials.refresh(request)
            
            # Save refreshed token
            token_data = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes
            }
            
            with open('token.json', 'w') as token_file:
                json.dump(token_data, token_file)
                
            print("Token refreshed successfully")
            return True
    except Exception as e:
        print(f"Error refreshing token: {str(e)}")
        return False

def is_token_expired() -> bool:
    """Check if the stored token is expired and try to refresh it"""
    try:
        if not os.path.exists('token.json'):
            print("No token file exists")
            return True
            
        try:
            with open('token.json', 'r', encoding='utf-8') as token_file:
                token_data = json.load(token_file)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            print(f"Error reading token file: {str(e)}")
            clear_token()
            return True
            
        credentials = Credentials.from_authorized_user_info(token_data)
        
        # Only refresh if actually expired
        if not credentials.valid and credentials.expired:
            if credentials.refresh_token:
                if refresh_token(credentials):
                    return False
                return True
            return True
            
        return False  # Token is still valid
    except Exception as e:
        print(f"Error checking token expiration: {str(e)}")
        return True

@router.get("/check-auth", response_model=None)
async def check_auth():
    """Check if user is authenticated with valid token"""
    try:
        if not os.path.exists('token.json'):
            return JSONResponse({"status": "unauthenticated"})
            
        if is_token_expired():
            clear_token()  # Clear invalid token
            return JSONResponse({"status": "unauthenticated"})
            
        return JSONResponse({"status": "authenticated"})
    except Exception as e:
        print(f"Error in check_auth: {str(e)}")
        return JSONResponse({"status": "unauthenticated"})

@router.get("/auth/gmail", response_model=None)
async def gmail_auth():
    try:
        if is_token_expired():
            clear_token()
        
        flow = Flow.from_client_secrets_file(
            'credentials.json',
            scopes=[
                'https://www.googleapis.com/auth/gmail.readonly',
                'https://www.googleapis.com/auth/userinfo.email',
                'openid'
            ],
            redirect_uri="http://localhost:8000/auth/gmail/callback"
        )
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        active_states.add(state)
        return RedirectResponse(url=authorization_url)
        
    except Exception as e:
        print(f"Error initiating auth: {str(e)}")
        return RedirectResponse(url="http://localhost:3000/login?error=auth_failed")

@router.get("/auth/gmail/callback", response_model=None)
async def gmail_callback(request: Request, code: str, state: str):
    try:
        if state not in active_states:
            raise HTTPException(status_code=400, detail="Invalid state parameter")
        
        active_states.remove(state)
        
        flow = Flow.from_client_secrets_file(
            'credentials.json',
            scopes=[
                'https://www.googleapis.com/auth/gmail.readonly',
                'https://www.googleapis.com/auth/userinfo.email',
                'openid'
            ],
            redirect_uri="http://localhost:8000/auth/gmail/callback"
        )
        
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        token_data = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }
        
        with open('token.json', 'w') as token_file:
            json.dump(token_data, token_file)
            
        print("Token saved successfully")
        return RedirectResponse(url="http://localhost:3000")
        
    except Exception as e:
        print(f"Error in callback: {str(e)}")
        return RedirectResponse(url="http://localhost:3000/login?error=auth_failed")

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

@router.get("/test-auth")
async def test_auth():
    """Test if authentication is working"""
    try:
        if is_token_expired():
            return JSONResponse({"status": "unauthenticated"})
            
        with open('token.json', 'r') as token_file:
            token_data = json.load(token_file)
            
        return JSONResponse({
            "status": "authenticated",
            "token_info": {
                "has_token": bool(token_data.get('token')),
                "has_refresh_token": bool(token_data.get('refresh_token')),
                "scopes": token_data.get('scopes')
            }
        })
    except Exception as e:
        print(f"Error in test_auth: {str(e)}")
        return JSONResponse({"status": "error", "message": str(e)})

@router.get("/test-token", response_model=None)
async def test_token():
    """Test the current token status and Gmail API access"""
    try:
        if not os.path.exists('token.json'):
            return JSONResponse({
                "status": "no_token",
                "message": "No token file found"
            })

        # Read the token
        with open('token.json', 'r') as token_file:
            token_data = json.load(token_file)

        # Create credentials
        credentials = Credentials.from_authorized_user_info(token_data)

        # Test Gmail API access
        gmail_service = build('gmail', 'v1', credentials=credentials)
        
        # Try to get user profile
        profile = gmail_service.users().getProfile(userId='me').execute()
        
        return JSONResponse({
            "status": "success",
            "token_info": {
                "has_access_token": bool(credentials.token),
                "has_refresh_token": bool(credentials.refresh_token),
                "is_expired": credentials.expired,
                "scopes": credentials.scopes,
                "email": profile.get('emailAddress'),
                "last_refresh": datetime.now().isoformat()
            }
        })

    except Exception as e:
        print(f"Error testing token: {str(e)}")
        return JSONResponse({
            "status": "error",
            "message": str(e)
        })

@router.get("/fetch-emails", response_model=None)
async def fetch_emails_endpoint():
    """Fetch emails from Gmail and store them in the database"""
    try:
        # Get Gmail service
        service = authenticate_gmail()
        
        # Get folder ID
        folder_id = list_labels(service)
        if not folder_id:
            return JSONResponse({
                "status": "error",
                "message": "Folder 'Da guardare' not found"
            })
            
        # List messages in the folder
        results = service.users().messages().list(
            userId='me',
            labelIds=[folder_id],
            maxResults=10  # Start with just 10 emails for testing
        ).execute()
        
        messages = results.get('messages', [])
        if not messages:
            return JSONResponse({
                "status": "success",
                "message": "No messages found in folder"
            })
            
        stored_count = 0
        for message in messages:
            # Get full message details
            msg = service.users().messages().get(
                userId='me',
                id=message['id'],
                format='full'
            ).execute()
            
            # Extract headers
            headers = msg.get('payload', {}).get('headers', [])
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No subject')
            
            # Extract body
            payload = msg.get('payload', {})
            body = ""
            if 'parts' in payload:
                for part in payload['parts']:
                    if part.get('mimeType') == 'text/plain':
                        if 'data' in part['body']:
                            body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                            break
            elif 'body' in payload and 'data' in payload['body']:
                body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
            
            # Store in database
            try:
                conn = psycopg2.connect(**DB_CONFIG)
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO emails (sender, subject, body, received_at)
                    VALUES (%s, %s, %s, NOW())
                    ON CONFLICT (id) DO NOTHING
                    RETURNING id;
                """, (sender, subject, body))
                conn.commit()
                stored_count += 1
                print(f"Stored email: {subject[:50]}...")
            except Exception as db_error:
                print(f"Error storing email: {str(db_error)}")
            finally:
                cur.close()
                conn.close()
        
        return JSONResponse({
            "status": "success",
            "message": f"Processed {len(messages)} messages, stored {stored_count} in database",
            "details": {
                "folder_id": folder_id,
                "messages_found": len(messages),
                "messages_stored": stored_count
            }
        })
            
    except Exception as e:
        print(f"Error fetching emails: {str(e)}")
        return JSONResponse({
            "status": "error",
            "message": str(e)
        })

@router.get("/check-database", response_model=None)
async def check_database():
    """Check what emails are stored in the database"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Get total count
        cur.execute("SELECT COUNT(*) FROM emails")
        total_count = cur.fetchone()[0]
        
        # Get sample of emails
        cur.execute("""
            SELECT id, sender, subject, received_at 
            FROM emails 
            ORDER BY received_at DESC 
            LIMIT 10
        """)
        emails = cur.fetchall()
        
        formatted_emails = []
        for email in emails:
            formatted_emails.append({
                "id": email[0],
                "sender": email[1],
                "subject": email[2],
                "received_at": email[3].isoformat() if email[3] else None
            })
            
        cur.close()
        conn.close()
        
        return JSONResponse({
            "status": "success",
            "total_emails": total_count,
            "sample_emails": formatted_emails
        })
            
    except Exception as e:
        print(f"Error checking database: {str(e)}")
        return JSONResponse({
            "status": "error",
            "message": str(e)
        })
