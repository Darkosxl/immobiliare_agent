from fastapi import FastAPI
import os 
import requests
from datetime import datetime, timedelta

app = FastAPI()

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

    response = requests.post(url, json=body)
    print(response.json()["status"])
    return response.json()["status"]

def lookup_apartment_info_tool(args):

    return


@app.route("/vapi/tool-call", methods=["POST"])
def tool_call():
    data = request.json
    tool_calls = data["message"]["toolCalls"]
    for tool_call in tool_calls:
        tool_name = tool_call["function"]["name"]
        args = tool_call["function"]["arguments"]
        
        if tool_name == "Check_google_calendar_availability":
            calendar_check_availability_tool(args)

        elif tool_name == "Setup_google_calendar_meeting":
            calendar_meeting_create_tool(args)
        elif tool_name == "Lookup_apartment_info":
            lookup_apartment_info_tool(args)



