from fastapi import FastAPI
import os 
import requests

app = FastAPI()

def calendar_check_availability_tool(args):
    email = args["caller_email"]
    meeting_time = args["meeting_time"]
    url = ""
    json = {

    }
    return
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
        "description": "Meeting for apartment viewing: " + str(address)
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



