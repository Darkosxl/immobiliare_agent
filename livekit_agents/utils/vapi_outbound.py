import os
import requests
import sys

from dotenv import load_dotenv

load_dotenv()

VAPI_API_KEY = os.getenv("VAPI_API_KEY")
ASSISTANT_ID = os.getenv("VAPI_ASSISTANT_ID")
PHONE_NUMBER_ID = os.getenv("VAPI_ITA_NUMBER")


def call(number: str):
    """Make an outbound call via VAPI"""
    response = requests.post(
        "https://api.vapi.ai/call",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {VAPI_API_KEY}"
        },
        json={
            "assistantId": ASSISTANT_ID,
            "phoneNumberId": PHONE_NUMBER_ID,
            "customer": {"number": number}
        }
    )
    print(f"Call initiated: {response.json()}")
    return response.json()


if __name__ == "__main__":
    number = sys.argv[1] if len(sys.argv) > 1 else "+393517843713"
    call(number)
