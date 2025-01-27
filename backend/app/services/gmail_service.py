import os
import pickle
import base64
import psycopg2
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from bs4 import BeautifulSoup
import openai
import json

# Load environment variables from .env file
load_dotenv()

# Database credentials from environment variables
DB_CONFIG = {
    'dbname': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT'),
}

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
CREDENTIALS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'credentials.json')
TOKEN_FILE = os.path.join(os.path.dirname(__file__), 'token.json')

openai.api_key = os.getenv("OPENAI_API_KEY")

def authenticate_gmail():
    """Handles Gmail API authentication and returns a service instance."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, 'rb') as token:
                creds = pickle.load(token)
        except Exception:
            if os.path.exists(TOKEN_FILE):
                os.remove(TOKEN_FILE)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                if os.path.exists(TOKEN_FILE):
                    os.remove(TOKEN_FILE)
                creds = None
        
        if not creds:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, 
                SCOPES,
                redirect_uri=os.getenv('OAUTH_REDIRECT_URI', 'http://localhost:8080')
            )
            # Use the frontend URL for the OAuth flow
            auth_url = flow.authorization_url()[0]
            return {"auth_url": auth_url}

    return build('gmail', 'v1', credentials=creds)

def list_labels(service):
    """Fetch all labels and find the configured folder."""
    try:
        # Get the configured folder name
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'folder_config.json')
        folder_name = "Da guardare"  # Default name
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
                folder_name = config.get('folder_name', folder_name)
        
        print(f"Looking for folder: {folder_name}")  # Debug log
        
        # List all labels
        results = service.users().labels().list(userId='me').execute()
        labels = results.get('labels', [])
        
        print("Available labels:")  # Debug log
        for label in labels:
            print(f"- {label['name']} (ID: {label['id']})")  # Debug log

        # Find the matching label
        for label in labels:
            if label['name'].lower() == folder_name.lower():
                print(f"Found matching label: {label['name']} with ID: {label['id']}")
                return label['id']
        
        print(f"Label '{folder_name}' not found!")
        return None

    except Exception as e:
        print(f"Error listing labels: {str(e)}")
        return None

def extract_plain_text(payload):
    """Extract plain text content from an email's payload."""
    email_text = ""

    if 'parts' in payload:
        for part in payload['parts']:
            email_text += extract_plain_text(part)
    else:
        mime_type = payload.get('mimeType')
        body_data = payload.get('body', {}).get('data', '')

        if body_data:
            decoded_body = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='ignore')
            if mime_type == 'text/plain':
                email_text += decoded_body + "\n"
            elif mime_type == 'text/html':
                soup = BeautifulSoup(decoded_body, 'html.parser')
                email_text += soup.get_text() + "\n"  # Extract plain text from HTML

    return email_text.strip()

def fetch_emails():
    """Fetch emails from 'Da guardare' label and store them in the database."""
    service = authenticate_gmail()
    label_id = list_labels(service)

    if not label_id:
        return

    results = service.users().messages().list(userId='me', labelIds=[label_id]).execute()
    messages = results.get('messages', [])

    if not messages:
        print('No messages found in "Da guardare" folder.')
        return

    email_data = []

    for message in messages:
        msg = service.users().messages().get(userId='me', id=message['id']).execute()
        payload = msg.get('payload', {})
        headers = payload.get('headers', [])

        email_from = email_subject = email_body = ""

        # Extract sender and subject
        for header in headers:
            if header['name'] == 'From':
                email_from = header['value']
            elif header['name'] == 'Subject':
                email_subject = header['value']

        # Extract email body
        email_body = extract_plain_text(payload)

        print("=" * 50)
        print(f"From: {email_from}")
        print(f"Subject: {email_subject}")
        print(f"Body length: {len(email_body)} characters")
        print("=" * 50)

        email_data.append((email_from, email_subject, email_body))

    store_emails_in_db(email_data)

def store_emails_in_db(email_data):
    """Store extracted emails in PostgreSQL database."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        for email in email_data:
            cur.execute("""
                INSERT INTO emails (sender, subject, body)
                VALUES (%s, %s, %s);
            """, email)

        conn.commit()
        cur.close()
        conn.close()
        print("Emails successfully stored in the database.")

    except Exception as e:
        print(f"Database error: {e}")

# New functions to search and summarize emails
def search_emails(query):
    """Search emails matching the query by sender, subject, or content."""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    query_param = f"%{query}%"
    cur.execute("""
        SELECT id, sender, subject, received_at 
        FROM emails 
        WHERE sender ILIKE %s OR subject ILIKE %s OR body ILIKE %s
    """, (query_param, query_param, query_param))
    
    results = cur.fetchall()
    cur.close()
    conn.close()
    
    emails = [{"id": row[0], "sender": row[1], "subject": row[2], "received_at": row[3]} for row in results]
    return emails

def summarize_email(email_id):
    """Fetch email content and summarize it using OpenAI."""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT body FROM emails WHERE id = %s", (email_id,))
    email_body = cur.fetchone()
    cur.close()
    conn.close()

    if not email_body:
        return "No email found with the given ID."
    
    # Send to OpenAI for summarization
    response = openai.ChatCompletion.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": "Summarize the following email content:"},
            {"role": "user", "content": email_body[0]}
        ]
    )
    
    return response['choices'][0]['message']['content']

def logout():
    """Remove Gmail API credentials."""
    try:
        if os.path.exists(TOKEN_FILE):
            os.remove(TOKEN_FILE)
            return {"message": "Successfully logged out"}
        else:
            return {"message": "No active session found"}
    except Exception as e:
        print(f"Error during logout: {e}")
        return {"error": f"Failed to logout: {str(e)}"}

def is_authenticated():
    """Check if there's a valid authentication token."""
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, 'rb') as token:
                creds = pickle.load(token)
                return creds and creds.valid
        except Exception:
            return False
    return False

def search_messages(service, query: str, label_id: str = None):
    """Search for messages in Gmail."""
    try:
        print(f"Searching in label_id: {label_id}")
        
        # Get all messages in the label
        results = service.users().messages().list(
            userId='me',
            labelIds=[label_id],
            maxResults=100
        ).execute()

        messages = results.get('messages', [])
        
        if not messages:
            print("No messages found in the label")
            return []

        detailed_messages = []
        # Keep the original query for exact matches
        query_exact = query.lower().strip()
        # Also split into terms for broader matching if needed
        query_terms = query_exact.split()
        print(f"Search query: {query_exact}")
        
        for message in messages:
            # Get full message content including body
            msg = service.users().messages().get(
                userId='me',
                id=message['id'],
                format='full'
            ).execute()

            # Extract headers
            headers = msg.get('payload', {}).get('headers', [])
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No subject')

            # Extract body content
            body = ""
            if 'parts' in msg.get('payload', {}):
                for part in msg['payload']['parts']:
                    if part.get('mimeType') == 'text/plain':
                        body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                        break
            elif 'body' in msg.get('payload', {}):
                if 'data' in msg['payload']['body']:
                    body = base64.urlsafe_b64decode(msg['payload']['body']['data']).decode('utf-8')

            # If no search terms, include all messages
            if not query_exact:
                detailed_messages.append({
                    'id': msg['id'],
                    'sender': sender,
                    'subject': subject
                })
                continue

            # Convert to lowercase for case-insensitive matching
            sender_lower = sender.lower()
            subject_lower = subject.lower()
            body_lower = body.lower()

            # First, check for exact matches in sender or subject
            if (query_exact in sender_lower or query_exact in subject_lower):
                detailed_messages.append({
                    'id': msg['id'],
                    'sender': sender,
                    'subject': subject
                })
                print(f"Exact match found - Subject: {subject}, Sender: {sender}")
                continue

            # If no exact match, then check if ALL terms appear in the body
            # This ensures we only match when all search terms are present
            if all(term in body_lower for term in query_terms):
                detailed_messages.append({
                    'id': msg['id'],
                    'sender': sender,
                    'subject': subject
                })
                print(f"Body match found - Subject: {subject}, Sender: {sender}")

        print(f"Found {len(detailed_messages)} matching messages")
        return detailed_messages

    except Exception as e:
        print(f"Error in search_messages: {str(e)}")
        raise e

if __name__ == "__main__":
    fetch_emails()
