import asyncio
import json
import os
import sys

from dotenv import load_dotenv
from livekit import api
import time

load_dotenv()

async def main():
    # Check password
    expected_password = os.environ.get("OUTBOUND_CALLING_PASSWORD")
    if not expected_password:
        print("Error: OUTBOUND_CALLING_PASSWORD not set in environment")
        sys.exit(1)

    password = input("Enter password: ")
    if password != expected_password:
        print("Error: Invalid password")
        sys.exit(1)

    # Get phone number from argument
    if len(sys.argv) < 2:
        print("Usage: python outbound_dispatch.py <phone_number>")
        print("Example: python outbound_dispatch.py +393517843713")
        sys.exit(1)

    phone_to_call = sys.argv[1]

    # Validate phone format
    if not phone_to_call.startswith("+"):
        print("Error: Phone number must be in E.164 format (e.g., +393517843713)")
        sys.exit(1)

    lk = api.LiveKitAPI()

    room_name = f"sip_room_1_{phone_to_call[-4:]}_{int(time.time())}"

    # 1. Create room with phone number in metadata
    await lk.room.create_room(
        api.CreateRoomRequest(
            name=room_name,
            metadata=json.dumps({"phone_number": phone_to_call})
        )
    )

    # 2. Dispatch your agent to this room
    dispatch = await lk.agent_dispatch.create_dispatch(
        api.CreateAgentDispatchRequest(
            room=room_name,
            agent_name="RealEstate-Outbound-Agent",
        )
    )
    print(f"Calling {phone_to_call}...")
    await lk.aclose()

asyncio.run(main())
