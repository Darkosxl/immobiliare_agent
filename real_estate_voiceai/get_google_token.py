import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Scopes required
SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_token():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Create a client config dictionary from env vars
            client_config = {
                "installed": {
                    "client_id": os.environ.get("GOOGLE_CLIENT_ID"),
                    "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET"),
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": ["http://localhost"]
                }
            }
            
            flow = InstalledAppFlow.from_client_config(
                client_config, SCOPES)
            creds = flow.run_local_server(port=0)
            
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
            
    return creds.token

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    if not os.environ.get("GOOGLE_CLIENT_ID") or not os.environ.get("GOOGLE_CLIENT_SECRET"):
        print("Error: GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET not found in .env")
        exit(1)
        
    print("Opening browser for authentication...")
    token = get_token()
    print(f"\nSUCCESS! Here is your access token:\n\n{token}\n")
    print("I will now append this to your .env file automatically.")
    
    # Read current .env
    with open(".env", "r") as f:
        lines = f.readlines()
        
    # Remove existing GOOGLE_ACCESS_TOKEN if any
    lines = [line for line in lines if not line.startswith("GOOGLE_ACCESS_TOKEN=")]
    
    # Append new token
    lines.append(f"\nGOOGLE_ACCESS_TOKEN={token}\n")
    
    with open(".env", "w") as f:
        f.writelines(lines)
        
    print("Updated .env with new token.")
