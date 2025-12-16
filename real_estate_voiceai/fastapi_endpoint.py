from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
import os 
import json
import requests
from datetime import datetime, timedelta
import uvicorn
import threading
import gmail_poller

# Start Gmail Poller in background
def start_gmail_poller():
    print("Starting Gmail Poller Thread...")
    while True:
        try:
            print(f"[{datetime.now().strftime('%X')}] Polling for emails...")
            gmail_poller.check_emails()
        except Exception as e:
            print(f"Gmail Poller Error: {e}")
        import time
        time.sleep(60)

threading.Thread(target=start_gmail_poller, daemon=True).start()

def get_google_token():
    try:
        with open("google_tokens.json", "r") as f:
            tokens = json.load(f)
            return tokens.get("access_token")
    except Exception as e:
        print(f"Error reading google_tokens.json: {e}")
        return None

def calendar_check_availability_tool(args):
    token = get_google_token()
    if not token:
        return "Error: Google Calendar not connected. Please connect via the Dashboard."

    meeting_time = args["meeting_time"]
    dt = datetime.fromisoformat(meeting_time.replace("Z", "+00:00"))
    end_time_dt = dt + timedelta(hours=0.5)
    end_time = end_time_dt.isoformat()
    
    # We need the calendar ID. For now, assume 'primary' or use the user's email if we had it.
    # The original code used os.getenv("GOOGLE_CALENDAR_EMAIL"). 
    # Let's use 'primary' which refers to the authenticated user's main calendar.
    calendar_id = "primary"
    
    url = "https://www.googleapis.com/calendar/v3/freeBusy"
    json_body = {
        "timeMin": meeting_time,
        "timeMax": end_time,
        "items": [
            {
            "id": calendar_id,
            }
        ]
    }
    response = requests.post(url, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, json=json_body)
    
    if response.status_code != 200:
        return f"Error checking availability: {response.text}"
        
    try:
        busy_info = response.json()["calendars"][calendar_id]["busy"]
        return "Busy" if busy_info else "Available"
    except KeyError:
        return "Error parsing calendar response"
    
def calendar_meeting_create_tool(args):
    token = get_google_token()
    if not token:
        return "Error: Google Calendar not connected. Please connect via the Dashboard."

    email = args["caller_email"]
    meeting_time = args["meeting_time"]
    address = args["meeting_address"]

    url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
    body = {
        "start": {
            "dateTime": meeting_time,
            "timeZone": "Europe/Rome"
        },
        "end": {
            "dateTime": meeting_time, # This looks like a bug in original code (0 duration). Let's fix it.
            "timeZone": "Europe/Rome"
        },
        "attendees": [
            {"email": email}
        ],
        "description": "Meeting for apartment viewing: " + str(address),
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "email", "minutes": 24 * 60},
                {"method": "popup", "minutes": 10},
            ],
        },
    }
    
    # Fix end time to be +1 hour
    dt = datetime.fromisoformat(meeting_time.replace("Z", "+00:00"))
    end_dt = dt + timedelta(hours=1)
    body["end"]["dateTime"] = end_dt.isoformat()

    response = requests.post(url, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, json=body)
    if response.status_code != 200:
        print(f"Error creating meeting: {response.text}")
        return f"Error: {response.text}"
        
    print(response.json().get("status"))

def lookup_apartment_info_tool(args):

    return



app = FastAPI()

@app.post("/vapi/tool-call")
async def tool_call(request: Request):
    data = await request.json()
    print(f"Received payload: {data}")
    
    message = data.get("message", {})
    if message.get("type") != "tool-calls":
        print(f"Received message type: {message.get('type')}. Ignoring.")
        return {"results": []}
        
    tool_calls = message.get("toolCallList", [])
    results = []
    for tool_call in tool_calls:
        tool_name = tool_call["function"]["name"]
        args = tool_call["function"]["arguments"]
        
        result = None
        if tool_name == "Check_google_calendar_availability":
            result = calendar_check_availability_tool(args)
        elif tool_name == "Setup_google_calendar_meeting":
            result = calendar_meeting_create_tool(args)
        elif tool_name == "Lookup_apartment_info":
            result = lookup_apartment_info_tool(args)
            
        results.append({
            "toolCallId": tool_call["id"],
            "result": str(result)
        })
        
    return {"results": results}

    return {"results": results}

@app.get("/connect")
def connect_google_calendar():
    from google_auth_oauthlib.flow import Flow
    
    # Create the flow using the client secrets
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": os.environ.get("GOOGLE_CLIENT_ID"),
                "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET"),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=['https://www.googleapis.com/auth/calendar']
    )
    
    # IMPORTANT: You must manually update this redirect_uri in your Google Console
    # to match your current Ngrok URL + /oauth2callback
    # Example: https://f9a17b6593f7.ngrok-free.app/oauth2callback
    # For now, we will try to detect it from the request if possible, or hardcode it.
    # Since we are behind ngrok, we need the public URL.
    # Let's assume the user will set a REDIRECT_URI env var or we use a placeholder.
    redirect_uri = os.environ.get("REDIRECT_URI", "http://localhost:8000/oauth2callback")
    
    flow.redirect_uri = redirect_uri
    
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    
    return {"url": authorization_url, "message": "Go to this URL to authorize: " + authorization_url}

@app.get("/oauth2callback")
def oauth2callback(code: str):
    from google_auth_oauthlib.flow import Flow
    
    redirect_uri = os.environ.get("REDIRECT_URI", "http://localhost:8000/oauth2callback")

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": os.environ.get("GOOGLE_CLIENT_ID"),
                "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET"),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=['https://www.googleapis.com/auth/calendar']
    )
    flow.redirect_uri = redirect_uri
    
    # Fetch the token
    flow.fetch_token(code=code)
    credentials = flow.credentials
    
    # Save to .env
    token = credentials.token
    refresh_token = credentials.refresh_token
    
    # Read current .env
    env_path = ".env"
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            lines = f.readlines()
    else:
        lines = []
        
    # Remove existing tokens
    lines = [line for line in lines if not line.startswith("GOOGLE_ACCESS_TOKEN=") and not line.startswith("GOOGLE_REFRESH_TOKEN=")]
    
    # Append new tokens
    lines.append(f"\nGOOGLE_ACCESS_TOKEN={token}\n")
    if refresh_token:
        lines.append(f"GOOGLE_REFRESH_TOKEN={refresh_token}\n")
    
    with open(env_path, "w") as f:
        f.writelines(lines)
        
    # Update the running process environment variable so we don't need a restart
    os.environ["GOOGLE_ACCESS_TOKEN"] = token
        
    return {"status": "success", "message": "Token saved! You can close this window."}

@app.post("/disconnect")
def disconnect_google_calendar():
    # Remove from .env
    env_path = ".env"
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            lines = f.readlines()
        
        lines = [line for line in lines if not line.startswith("GOOGLE_ACCESS_TOKEN=") and not line.startswith("GOOGLE_REFRESH_TOKEN=")]
        
        with open(env_path, "w") as f:
            f.writelines(lines)
            
    # Remove from running process
    if "GOOGLE_ACCESS_TOKEN" in os.environ:
        del os.environ["GOOGLE_ACCESS_TOKEN"]
    if "GOOGLE_REFRESH_TOKEN" in os.environ:
        del os.environ["GOOGLE_REFRESH_TOKEN"]
        
    print("Google Calendar disconnected.")
    return {"status": "success", "message": "Disconnected"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)



