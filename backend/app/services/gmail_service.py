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

import base64
import requests
import re
from bs4 import BeautifulSoup

def fetch_emails():
    """Fetches emails from the 'Da guardare' label and extracts plain text content."""
    service = authenticate_gmail()
    label_id = list_labels()

    if label_id:
        results = service.users().messages().list(userId='me', labelIds=[label_id]).execute()
        messages = results.get('messages', [])

        if not messages:
            print('No messages found in "Da guardare" folder.')
        else:
            for message in messages:
                msg = service.users().messages().get(userId='me', id=message['id']).execute()
                payload = msg.get('payload', {})
                headers = payload.get('headers', [])

                email_from = email_subject = email_body = ""
                received_date = msg.get('internalDate', '')

                # Extract sender and subject from headers
                for header in headers:
                    if header['name'] == 'From':
                        email_from = header['value']
                    elif header['name'] == 'Subject':
                        email_subject = header['value']

                # Extract plain text content
                email_body = extract_plain_text(payload)

               # Store or print the extracted information in a concise way
                print("=" * 50)
                print(f"From: {email_from}")
                print(f"Subject: {email_subject}")
                print(f"Body length: {len(email_body)} characters")  # Show body length instead of full text
                print("=" * 50)



def extract_plain_text(payload):
    """ Extracts the plain text content from an email's payload. """
    email_text = ""

    if 'parts' in payload:
        # Recursively process multi-part emails
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
