import os
import datetime
from vapi import Vapi
from dotenv import load_dotenv


class VoiceAgent:
    def __init__(self, agency, listing=None, assistant_id=None, caller_name=None):
        load_dotenv()
        self.agency = agency
        self.listing = listing or []
        self.assistant_id = assistant_id
        self.caller_name = caller_name
        self.client = Vapi(token=os.getenv("VAPI_API_KEY"))
        self.datetime = datetime.datetime.now()
        self.assistant = None

    def start(self):
        if self.assistant_id == None:
            self._create_assistant()
        else:
            self._get_assistant()

    def _create_assistant(self):
        today_date = self.datetime.strftime("%A, %d %B %Y")
        caller_context = f"\n            CHIAMATA: Stai chiamando {self.caller_name}." if self.caller_name else ""
        system_prompt = f"""
            Sei Chiara, segretaria di {self.agency}.
            Il tuo obiettivo è solo uno: fissare appuntamenti per le visite.
            
            DATA DI OGGI: {today_date}{caller_context}

            DATI IMMOBILE:
            {self.listing}

            REGOLE:
            1. Risposte brevissime (massimo 1 frase).
            2. Se chiedono dati non in lista, dì che non lo sai.
            3. Spingi sempre per la visita nei giorni disponibili.
            4. Parla italiano naturale.
            5. Qualsiasi indirizzo fornito è a Milano, Italia per default.
            """
        greeting = "Buongiorno" if self.datetime.time() < datetime.time(12, 0) else "Buonasera"

        self.assistant = self.client.assistants.create(
            name="Real Estate Assistant",
            transcriber={
                "provider": "deepgram",
                "model": "nova-3",
                "language": "it"
            },
            model={
                "provider": "google",
                "model": "gemini-2.5-flash",
                "messages": [{"role": "system", "content": system_prompt}],
                "toolIds": [
                    "47060d68-075e-425e-8b8c-4fe08cd8fde7", # Check_google_calendar_availability
                    "a75a9318-435f-4c98-84c8-e8895a69cca8", # Setup_google_calendar_meeting
                    "1b7ac49e-1206-45e0-8e32-9122ada314c7", # Lookup_apartment_info
                    "7b30bbe8-e543-4e8f-b903-a002f1e00929"  # end_call_tool (Vapi built-in)
                ]
            },
            voice={"provider": "openai", "voiceId": "alloy"},
            first_message=f"{greeting}, qui Chiara di {self.agency}. Come posso aiutarti?",
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
        print(f"Call initiated: {response}")
        return response
    
    def _get_assistant(self):
        self.assistant = self.client.assistants.get(self.assistant_id)