import asyncio
import json
import os
import uuid

from dotenv import load_dotenv
from livekit import api

load_dotenv()

async def main():
    lk = api.LiveKitAPI()

    phone_to_call = os.environ.get("OUTBOUND_PHONE_NUMBER", "+39XXXXXXXXX")
    room_name = f"outbound-{uuid.uuid4().hex[:8]}"

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

    print(f"Dispatched to {phone_to_call}")
    print(f"Room: {room_name}")

    await lk.aclose()

asyncio.run(main())
