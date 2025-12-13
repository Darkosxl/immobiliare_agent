import os
import datetime
from vapi import Vapi
from dotenv import load_dotenv


class VoiceAgentEN:
    """English version of VoiceAgent for testing purposes."""
    
    def __init__(self, agency, listing=None):
        load_dotenv()
        self.agency = agency
        self.listing = listing or []
        self.client = Vapi(token=os.getenv("VAPI_API_KEY"))
        self.datetime = datetime.datetime.now()
        self.assistant = None

    def start(self):
        self._create_assistant()

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
            name="Real Estate Assistant EN",
            transcriber={
                "provider": "deepgram",
                "model": "nova-2",
                "language": "en"
            },
            model={
                "provider": "google",
                "model": "gemini-2.5-flash",
                "messages": [{"role": "system", "content": system_prompt}]
            },
            voice={"provider": "openai", "voiceId": "alloy"},
            first_message=f"{greeting}, this is Sarah from {self.agency}. How can I help you?"
        )

    def initiate_call(self, to_call):
        response = self.client.calls.create(
            assistant_id=self.assistant.id,
            phone_number_id=os.getenv("VAPI_US_NUMBER"),
            customer={"number": to_call}
        )
        print(f"Call initiated: {response}")
        return response
