import os
import datetime
from vapi import Vapi
from dotenv import load_dotenv


class VoiceAgentEN:
    """English version of VoiceAgent for testing purposes."""
    
    def __init__(self, agency, listing=None, assistant_id=None, caller_name=None):
        load_dotenv()
        self.agency = agency
        self.listing = listing or []
        self.caller_name = caller_name
        self.client = Vapi(token=os.getenv("VAPI_API_KEY"))
        self.datetime = datetime.datetime.now()
        self.assistant = None
        self.assistant_id = assistant_id

    def start(self):
        if self.assistant_id == None:
            self._create_assistant()
        else:
            self._get_assistant()

    def _create_assistant(self):
        today_date = self.datetime.strftime("%A, %B %d, %Y")
        caller_context = f"\n            CALLER: You are calling {self.caller_name}." if self.caller_name else ""
        system_prompt = f"""
            You are Sarah, a secretary at {self.agency}.
            Your only goal is: scheduling property viewings.
            
            TODAY'S DATE: {today_date}{caller_context}

            PROPERTY DATA:
            {self.listing}

            RULES:
            1. Keep responses very short (max 1 sentence).
            2. If asked about data not in the list, say you don't know.
            3. Always push for scheduling a viewing on available days.
            4. Speak natural English.
            5. Any address given is in Milan, Italy by default. You don't need to ask for the city and the country, only the street address.
            """
        greeting = "Good morning" if self.datetime.time() < datetime.time(12, 0) else "Good afternoon"
        
        self.assistant = self.client.assistants.create(
            name="Nila",
            transcriber={
                "provider": "deepgram",
                "model": "nova-3",
                "language": "en"
            },
            model={
                "provider": "openai",
                "model": "gpt-5.2",
                "messages": [{"role": "system", "content": system_prompt}],
                "toolIds": [
                    "050c0248-89e5-4370-a3cf-a4f0cc0b73e8", # Setup_google_calendar_meeting
                    "1f95ff5c-6d9d-4a2a-89ee-e31f1d1dc67a", # Check_google_calendar_availability
                    "d08ffc43-a18d-4675-83d9-abfb64e7a598", # Lookup_apartment_infow
                    "7b30bbe8-e543-4e8f-b903-a002f1e00929"  # end_call_tool
                ]
            },
            voice={"provider": "openai", "voiceId": "alloy"},
            first_message=f"{greeting}, this is Sarah from {self.agency}. How can I help you?",
            voicemail_detection={
                "provider": "twilio",
                "enabled": True,
                "machineDetectionTimeout": 45,
                "machineDetectionSilenceTimeout": 10000
            }
        )

    def initiate_call(self, to_call):
        response = self.client.calls.create(
            assistant_id=self.assistant.id,
            phone_number_id=os.getenv("VAPI_ITA_NUMBER"),
            customer={"number": to_call}
        )
        print(f"Call initiated: {response}", flush=True)
        return response
    
    def _get_assistant(self):
        self.assistant = self.client.assistants.get(self.assistant_id)
