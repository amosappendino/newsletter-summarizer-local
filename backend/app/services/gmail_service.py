import os
import pickle
import base64
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# If modifying the SCOPES, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Path to your credentials.json
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.json'

def list_labels():
    """Fetch and print all labels for the authenticated user and find 'Da guardare'."""
    service = authenticate_gmail()

    # Call the Gmail API to fetch labels
    results = service.users().labels().list(userId='me').execute()
    labels = results.get('labels', [])

    if not labels:
        print('No labels found.')
    else:
        print('Labels:')
        for label in labels:
            print(f"Label Name: {label['name']}, Label ID: {label['id']}")
            if label['name'] == "Da guardare":
                print(f"Found 'Da guardare' label with ID: {label['id']}")
                return label['id']
    print("Label 'Da guardare' not found.")
    return None



def authenticate_gmail():
    """Handles authentication and returns a Gmail API service instance."""
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time.
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=8000)

        # Save the credentials for the next run
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)

    # Build the Gmail API service
    service = build('gmail', 'v1', credentials=creds)
    return service

def fetch_emails():
    """Fetches emails from the 'Da guardare' label."""
    service = authenticate_gmail()

    # Hardcoded label ID for 'Da guardare'
    label_id = 'Label_1410634696735130817'

    try:
        # Call the Gmail API to fetch emails from 'Da guardare' folder using the label ID
        results = service.users().messages().list(userId='me', labelIds=[label_id]).execute()
        messages = results.get('messages', [])

        if not messages:
            print('No messages found in "Da guardare" folder.')
        else:
            print(f"Found {len(messages)} messages in 'Da guardare' folder:\n")
            for message in messages:
                msg = service.users().messages().get(userId='me', id=message['id']).execute()
                payload = msg.get('payload', {})
                headers = payload.get('headers', [])

                email_from = next((header['value'] for header in headers if header['name'] == 'From'), 'Unknown sender')
                subject = next((header['value'] for header in headers if header['name'] == 'Subject'), 'No subject')

                snippet = msg.get('snippet', 'No snippet available')
                
                print(f"From: {email_from}")
                print(f"Subject: {subject}")
                print(f"Snippet: {snippet}")
                print("="*50)
    except Exception as e:
        print(f"An error occurred while fetching emails: {e}")
