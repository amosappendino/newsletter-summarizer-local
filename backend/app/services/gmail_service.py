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
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=8000)

        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)

    return build('gmail', 'v1', credentials=creds)

def list_labels(service):
    """Fetch all labels and find 'Da guardare' label ID."""
    results = service.users().labels().list(userId='me').execute()
    labels = results.get('labels', [])

    for label in labels:
        if label['name'] == "Da guardare":
            print(f"Found 'Da guardare' label with ID: {label['id']}")
            return label['id']
    
    print("Label 'Da guardare' not found.")
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

if __name__ == "__main__":
    fetch_emails()
