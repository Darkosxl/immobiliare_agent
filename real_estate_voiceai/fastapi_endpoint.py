from fastapi import FastAPI, Request
import os 
import requests
from datetime import datetime, timedelta
import uvicorn


def calendar_check_availability_tool(args):

    
    meeting_time = args["meeting_time"]
    dt = datetime.fromisoformat(meeting_time.replace("Z", "+00:00"))
    end_time_dt = dt + timedelta(hours=0.5)
    end_time = end_time_dt.isoformat()
    url = "https://www.googleapis.com/calendar/v3/freeBusy"
    json = {
        "timeMin": meeting_time,
        "timeMax": end_time,
        "items": [
            {
            "id": os.getenv("GOOGLE_CALENDAR_EMAIL"),
            }
        ]
    }
    response = requests.post(url, headers={"Authorization": f"Bearer {os.getenv('GOOGLE_ACCESS_TOKEN')}", "Content-Type": "application/json"}, json=json)
    print(response.json()["calendars"][os.getenv("GOOGLE_CALENDAR_EMAIL")]["busy"])
    return response.json()["calendars"][os.getenv("GOOGLE_CALENDAR_EMAIL")]["busy"]
    
def calendar_meeting_create_tool(args):
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
            "dateTime": meeting_time,
            "timeZone": "Europe/Rome"
        },
        "attendees": [
            {"email": email},
            {"email": os.getenv("GOOGLE_CALENDAR_EMAIL")}
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

    response = requests.post(url, headers={"Authorization": f"Bearer {os.getenv('GOOGLE_ACCESS_TOKEN')}", "Content-Type": "application/json"}, json=body)
    if response.status_code != 200:
        print(f"Error creating meeting: {response.text}")
        return f"Error: {response.text}"
        
    print(response.json().get("status"))
    return response.json().get("status")

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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)



