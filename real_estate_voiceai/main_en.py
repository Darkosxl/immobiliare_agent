import os
from dotenv import load_dotenv
import real_estate_voiceai.voice_assistant_en as va

load_dotenv()


def main():
    agent = va.VoiceAgentEN(agency="amorlabs", assistant_id=os.getenv("VAPI_ASSISTANT_ID"))
    agent.start()
    agent.initiate_call(os.getenv("TEST_PHONE_NUMBER"))


if __name__ == "__main__":
    main()
