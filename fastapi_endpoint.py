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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)



