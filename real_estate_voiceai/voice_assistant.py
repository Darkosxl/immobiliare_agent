import os
import datetime
from vapi import Vapi
from dotenv import load_dotenv


class VoiceAgent:
    def __init__(self, agency, listing=None, assistant_id=None):
        load_dotenv()
        self.agency = agency
        self.listing = listing or []
        self.assistant_id = assistant_id
        self.client = Vapi(token=os.getenv("VAPI_API_KEY"))
        self.datetime = datetime.datetime.now()
        self.assistant = None

    def start(self):
        if self.assistant_id == None:
            self._create_assistant()
        else:
            self._get_assistant()

    def _create_assistant(self):
        system_prompt = f"""
            Sei Chiara, segretaria di {self.agency}.
            Il tuo obiettivo è solo uno: fissare appuntamenti per le visite.

            DATI IMMOBILE:
            {self.listing}

            REGOLE:
            1. Risposte brevissime (massimo 1 frase).
            2. Se chiedono dati non in lista, dì che non lo sai.
            3. Spingi sempre per la visita nei giorni disponibili.
            4. Parla italiano naturale.
            """
        greeting = "Buongiorno" if self.datetime.time() < datetime.time(12, 0) else "Buonasera"

        self.assistant = self.client.assistants.create(
            name="Real Estate Assistant",
            transcriber={
                "provider": "deepgram",
                "model": "nova-2",
                "language": "it"
            },
            model={
                "provider": "google",
                "model": "gemini-2.5-flash",
                "messages": [{"role": "system", "content": system_prompt}],
                "toolIds": [
                    "050c0248-89e5-4370-a3cf-a4f0cc0b73e8", # Setup_google_calendar_meeting
                    "1f95ff5c-6d9d-4a2a-89ee-e31f1d1dc67a", # Check_google_calendar_availability
                    "d08ffc43-a18d-4675-83d9-abfb64e7a598", # Lookup_apartment_info
                    "def47154-c550-41a1-805b-eebeff324110"  # end_call_tool
                ]
            },
            voice={"provider": "openai", "voiceId": "alloy"},
            first_message=f"{greeting}, qui Chiara di {self.agency}. Come posso aiutarti?"
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