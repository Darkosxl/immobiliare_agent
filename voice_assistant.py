import os, requests
from vapi import Vapi
import datetime

class VoiceAgent:
    def __init__(self, agency, listing=None):
        self.agency = agency
        self.listing = listing or []
        self.client = Vapi(token=os.getenv("VAPI_API_KEY"))
        self.datetime = datetime.datetime.now()
        self.assistant = None


    def start(self):
        self._create_assistant()
        self._setup_phone_number()
    
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
        model={
            "provider": "google",
            "model": "gemini-2.5-flash",
            "messages": [{"role":"system", "content": system_prompt}] 
        },
        voice={"provider": "openai" , "voiceId": "alloy"},
        first_message=f"{greeting}, qui Chiara di {self.agency}. Come posso aiutarti?"
        ) 
    def _setup_phone_number(self):
        res = requests.post(
                "https://api.vapi.ai/phone-number",
                headers={
                    "Authorization": f"Bearer {os.getenv('VAPI_API_KEY')}",
                    "Content-Type": "application/json",
                },
                json={
                    "provider": "vapi",
                    "assistantId": self.assistant.id,
                    "numberDesiredAreaCode": "415",
                },
                timeout=30,
            )
        phone_number = res.json()
        print("Phone number:", phone_number["id"])

    async def initiate_call(self, to_call):
        await self.client.calls.create({
        assistantId=self.assistant.id,
        phone_number_id=os.getenv("VAPI_US_NUMBER"),
        customer={"number": to_call}
        })
        return "Call Finalised"

        