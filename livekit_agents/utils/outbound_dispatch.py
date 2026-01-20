import asyncio
import json
import os
import uuid

from dotenv import load_dotenv
from livekit import api
from livekit.protocol.sip import CreateSIPParticipantRequest, SIPParticipantInfo
import time

load_dotenv()

async def main():
    lk = api.LiveKitAPI()
    
    phone_to_call = os.environ.get("OUTBOUND_PHONE_NUMBER", "+39XXXXXXXXX")
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
    await lk.aclose()

asyncio.run(main())
