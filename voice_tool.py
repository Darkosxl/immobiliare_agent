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
        },
        "server": {
            "url": "http://localhost:8000/vapi/tool-call"
        }
    }
    

    response = requests.post(url, headers=headers, json=data)
    print(response.json())
    return response.json()

def setup_tools():
    print("Creating tools...")
    
    calendar_check_availability = create_tool(
        name="Check_google_calendar_availability",
        description="Use this tool to check if a specific time slot is free in the calendar before scheduling a meeting. Input the caller's email and the requested time.",
        parameters={
            "type": "object",
            "properties": {
                "meeting_time": {
                    "type": "string",
                    "description": "The time of the meeting (ISO 8601 format preferred)"
                }
            },
            "required": ["caller_email", "meeting_time"]
        }
    )

    calendar_meeting_create = create_tool(
        name="Setup_google_calendar_meeting",
        description="Use this tool to schedule a confirmed meeting in the calendar. REQUIRES: caller's email, meeting time, and the property address.",
        parameters={
            "type": "object",
            "properties": {
                "caller_email": {
                    "type": "string",
                    "description": "The email of the caller"
                },
                "meeting_time": {
                    "type": "string",
                    "description": "The time of the meeting (ISO 8601 format preferred)"
                },
                "meeting_address": {
                    "type": "string",
                    "description": "The address of the apartment"
                }
            },
            "required": ["caller_email", "meeting_time", "meeting_address"]
        }
    )

    lookup_apartment_info_tool = create_tool(
        name="Lookup_apartment_info",
        description="Use this tool to retrieve details about a specific apartment using its address. Useful for answering questions about price, size, or features.",
        parameters={
            "type": "object",
            "properties": {
                "address": {
                    "type": "string",
                    "description": "The address of the apartment"
                }
            },
            "required": ["address"]
        }
    )
    
    # Update Assistant with these tools
    assistant_id = os.getenv("VAPI_ASSISTANT_ID")
    if assistant_id:
        print(f"\nUpdating Assistant {assistant_id} with new tools...")
        url = f"https://api.vapi.ai/assistant/{assistant_id}"
        headers = {
            "Authorization": f"Bearer {os.getenv('VAPI_API_KEY')}",
            "Content-Type": "application/json"
        }
        
        # Get tool IDs
        tool_ids = [
            calendar_check_availability['id'],
            calendar_meeting_create['id'],
            lookup_apartment_info_tool['id']
        ]
        
        payload = {
            "model": {
                "toolIds": tool_ids
            }
        }
        
        # We need to be careful not to overwrite other model settings, 
        # but Vapi API usually allows patching just the toolIds if we use PATCH.
        # However, the requests library .patch method should be used.
        
        response = requests.patch(url, headers=headers, json=payload)
        print(f"Assistant Update Status: {response.status_code}")
        print(response.json())
    else:
        print("VAPI_ASSISTANT_ID not found in .env, skipping assistant update.")

setup_tools()