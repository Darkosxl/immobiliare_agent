import os
import datetime
from vapi import Vapi
from dotenv import load_dotenv


class VoiceAgentEN:
    """English version of VoiceAgent for testing purposes."""
    
    def __init__(self, agency, listing=None, assistant_id=None):
        load_dotenv()
        self.agency = agency
        self.listing = listing or []
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
        system_prompt = f"""
            You are Sarah, a secretary at {self.agency}.
            Your only goal is: scheduling property viewings.

            PROPERTY DATA:
            {self.listing}

            RULES:
            1. Keep responses very short (max 1 sentence).
            2. If asked about data not in the list, say you don't know.
            3. Always push for scheduling a viewing on available days.
            4. Speak natural English.
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
                "provider": "google",
                "model": "gemini-2.5-flash",
                "messages": [{"role": "system", "content": system_prompt}],
                "toolIds": [
                    "387257ab-4fd6-4f16-84a6-c95da5abd870", # Setup_google_calendar_meeting
                    "1928d0fd-87f6-4daf-88a2-a8b5e4b986ce", # Check_google_calendar_availability
                    "35092526-a4e2-41e6-b8c0-3e98c14c65f7", # Lookup_apartment_info
                    "7b30bbe8-e543-4e8f-b903-a002f1e00929"  # end_call_tool
                ]
            },
            voice={"provider": "openai", "voiceId": "alloy"},
            first_message=f"{greeting}, this is Sarah from {self.agency}. How can I help you?"
        )

    def initiate_call(self, to_call):
        response = self.client.calls.create(
            assistant_id=self.assistant.id,
            phone_number_id=os.getenv("VAPI_ITA_NUMBER"),
            customer={"number": to_call}
        )
        print(f"Call initiated: {response}")
        return response
    
    def _get_assistant(self):
        self.assistant = self.client.assistants.get(self.assistant_id)
