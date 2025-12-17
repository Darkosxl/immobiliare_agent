import os
import json
import time
import base64
import requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# Configuration
# Configuration
TARGET_SENDER = os.getenv("GOOGLE_CALENDAR_EMAIL")
if not TARGET_SENDER:
    print("WARNING: GOOGLE_CALENDAR_EMAIL not set in .env. Polling will likely fail to find specific emails.", flush=True)
else:
    print(f"Polling for emails from: {TARGET_SENDER}", flush=True)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
VAPI_ITA_NUMBER = os.getenv("VAPI_ITA_NUMBER")
VAPI_API_KEY = os.getenv("VAPI_API_KEY")
VAPI_ASSISTANT_ID = os.getenv("VAPI_ASSISTANT_ID")

def get_google_creds():
    try:
        with open("google_tokens.json", "r") as f:
            tokens = json.load(f)
            return Credentials(
                None,
                refresh_token=tokens.get("refresh_token"),
                token_uri="https://oauth2.googleapis.com/token",
                client_id=os.getenv("GOOGLE_CLIENT_ID"),
                client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
            )
    except Exception as e:
        print(f"Error reading google_tokens.json: {e}", flush=True)
        return None

def extract_phone_number(text):
    if not OPENROUTER_API_KEY:
        print("OPENROUTER_API_KEY not set", flush=True)
        return None

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "openai/gpt-5.2",
        "messages": [
            {"role": "system", "content": "You are a data extraction tool. Extract the phone number from the text. Return ONLY the phone number in E.164 format (e.g., +1234567890). If no number is found, return 'NONE'."},
            {"role": "user", "content": text}
        ]
    }
    
    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
        if response.status_code == 200:
            result = response.json()['choices'][0]['message']['content'].strip()
            return None if result == 'NONE' else result
        else:
            print(f"OpenRouter Error: {response.text}", flush=True)
            return None
    except Exception as e:
        print(f"Error calling OpenRouter: {e}", flush=True)
        return None

from voice_assistant_en import VoiceAgentEN

def trigger_vapi_call(phone_number):
    try:
        print(f"Initiating call to {phone_number} using VoiceAgentEN...", flush=True)
        # Initialize the agent (using "amorlabs" as default agency as seen in main_en.py)
        agent = VoiceAgentEN(agency="amorlabs")
        agent.start()
        agent.initiate_call(phone_number)
        print("Call initiated successfully.", flush=True)
    except Exception as e:
        print(f"Error triggering Vapi call: {e}", flush=True)

def check_emails():
    creds = get_google_creds()
    if not creds:
        print("No Google credentials found.", flush=True)
        return

    try:
        service = build('gmail', 'v1', credentials=creds)

        # Query for unread emails from the target sender
        if TARGET_SENDER:
            query = f"from:{TARGET_SENDER} is:unread"
        else:
            # Fallback: check all unread emails if no sender specified (for testing)
            print("No TARGET_SENDER configured. Checking ALL unread emails.", flush=True)
            query = "is:unread"

        print(f"Executing Gmail query: '{query}'", flush=True)
        results = service.users().messages().list(userId='me', q=query).execute()
        messages = results.get('messages', [])

        if not messages:
            print("No new messages.", flush=True)
            return

        for msg in messages:
            msg_id = msg['id']
            message = service.users().messages().get(userId='me', id=msg_id).execute()

            # Get body
            payload = message['payload']
            body = ""
            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain':
                        data = part['body']['data']
                        body = base64.urlsafe_b64decode(data).decode()
                        break
            else:
                data = payload['body']['data']
                body = base64.urlsafe_b64decode(data).decode()

            print(f"Processing email from {TARGET_SENDER}...", flush=True)

            # Extract Phone Number
            phone_number = extract_phone_number(body)

            if phone_number:
                print(f"Found phone number: {phone_number}. Initiating call...", flush=True)
                trigger_vapi_call(phone_number)
            else:
                print("No phone number found in email.", flush=True)

            # Mark as read
            service.users().messages().modify(userId='me', id=msg_id, body={'removeLabelIds': ['UNREAD']}).execute()

    except Exception as e:
        print(f"Error checking emails: {e}", flush=True)

if __name__ == "__main__":
    print("Starting Gmail Poller...")
    while True:
        print(f"[{time.strftime('%X')}] Polling for emails...")
        check_emails()
        time.sleep(60) # Check every minute
