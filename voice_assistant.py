import os
from vapi import Vapi


client = Vapi(token=os.getenv("VAPI_API_KEY"))

assistant = client.assistants.create(
    name="Real Estate Secretary",
    model={
        "provider": "google"
        "model": "gemini-2.5-flash" 
    },
    voice={"provider": "openai" ,   "model": "alloy"}
)    