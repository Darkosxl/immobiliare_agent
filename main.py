import os
import voice_assistant as va
from dotenv import load_dotenv

load_dotenv()


def main():
    agent = va.VoiceAgent(agency="amorlabs", assistant_id=os.getenv("VAPI_ASSISTANT_ID"))
    agent.start()
    agent.initiate_call(os.getenv("TEST_PHONE_NUMBER"))


if __name__ == "__main__":
    main()
