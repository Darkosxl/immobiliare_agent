import requests
import os
from dotenv import load_dotenv

def create_tool(name, description, parameters):
    url = "https://api.vapi.ai/tool"
    load_dotenv()

    headers = {
        "Authorization": f"Bearer {os.getenv('VAPI_API_KEY')}",
        "Content-Type": "application/json"
    }

    data = {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": parameters
        }
    },
    "server": {
        "url": "http://localhost:8000/vapi/tool-call"
    }

    response = requests.post(url, headers=headers, json=data)
    return response.json()

def setup_tools():
    calendar_check_availability = create_tool(
        name="Check_google_calendar_availability",
        description="Check if the time of the meeting is available in the calendar",
        parameters={
            "type":  "object" 
            "properties": {
                "caller_email": {
                    "type": "string"
                    "description": "The email of the caller"
                },
                "meeting_time": {
                    "type": "string"
                    "description": "The time of the meeting"
                } 
            "required": ["caller_email", "meeting_time"]    
            }
        }
    )

    calendar_meeting_create = create_tool(
        name="Setup_google_calendar_meeting",
        description="Set up a calendar meeting with the name of the caller, time of meeting and the address for the meeting",
        parameters={
            "type":  "object" 
            "properties": {
                "caller_email": {
                    "type": "string"
                    "description": "The email of the caller"
                },
                "meeting_time": {
                    "type": "string"
                    "description": "The time of the meeting"
                },
                "meeting_address": {
                    "type": "string"
                    "description": "The address of the apartment"
                } 
            "required": ["caller_name", "meeting_time", "meeting_address"]    
            }

        }
    )

    
    #this one is for later
    lookup_apartment_info_tool = create_tool(
        name="Lookup_apartment_info",
        description="Lookup apartment info with the address for information",
        parameters={
            "type":  "object" 
            "properties": {
                "address": {
                    "type": "string"
                    "description": "The address of the apartment"
                } 
            "required": ["address"]    
            }

        }
    )