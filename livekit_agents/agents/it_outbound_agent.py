import asyncio
import logging
import os
import json
#DONE 1: implement note_info tool (in tools/real_estate_tools.py)
#NOTE 2: flynumber telephony only works for inbound
#DONE 3: test the agent (tests written in tests/test_outbound_*.py)
#DONE 4: implement immobiliare_offers tool (in tools/real_estate_tools.py)

from dotenv import load_dotenv
from livekit import api, rtc
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    cli,
    WorkerOptions,
    room_io,
)
from livekit.plugins import openai, silero, deepgram, noise_cancellation, elevenlabs
from livekit.agents.voice import MetricsCollectedEvent
from livekit.plugins.turn_detector.multilingual import MultilingualModel

from agents.it_inbound_agent import RealEstateItalianAgent
from prompts.it_outbound_prompt import SYSTEM_PROMPT
from tools.calendar_tools import (
    schedule_meeting,
    end_call,
    get_existing_bookings,
    cancel_booking,
    check_available_slots
)
from tools.real_estate_tools import note_info, immobiliare_offers

logger = logging.getLogger("grok-agent")
logger.setLevel(logging.INFO)
load_dotenv(".env")

OUTBOUND_TRUNK_ID = os.getenv("OUTBOUND_TRUNK_ID")


class RealEstateItalianOutboundAgent(RealEstateItalianAgent):
    def __init__(self) -> None:
        # Call Agent.__init__ directly to override instructions and tools
        Agent.__init__(
            self,
            instructions=SYSTEM_PROMPT,
            tools=[
                schedule_meeting,
                note_info,
                immobiliare_offers,
                end_call,
                get_existing_bookings,
                cancel_booking,
                check_available_slots
            ]
        )
        self.participant: rtc.RemoteParticipant | None = None

    def set_participant(self, participant: rtc.RemoteParticipant):
        self.participant = participant

    async def on_enter(self):
        # Skip whitelist check for outbound - we're calling them
        await self.session.generate_reply(allow_interruptions=False)
    
async def entrypoint(ctx: JobContext):
    
    await ctx.connect()
    
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }
    dial_info = json.loads(ctx.room.metadata)
    participant_identity = dial_info["phone_number"]
    
    agent = RealEstateItalianOutboundAgent()
    
    session = AgentSession(
        stt=deepgram.STT(model="nova-3", language="it-IT"),
        llm=openai.LLM.with_x_ai(
           model="grok-4-fast-reasoning",
        ),
        tts=elevenlabs.TTS(
            voice_id="W71zT1VwIFFx3mMGH2uZ",
            model="eleven_multilingual_v2",
            api_key=os.getenv("ELEVENLABS_API_KEY")
        ),
        turn_detection=MultilingualModel(),
        vad=silero.VAD.load(),
        preemptive_generation=True,
        resume_false_interruption=True,
        false_interruption_timeout=1.0,
    )
    
    try:
        await ctx.api.sip.create_sip_participant(
            api.CreateSIPParticipantRequest(
                room_name=ctx.room.name,
                sip_trunk_id=OUTBOUND_TRUNK_ID,
                sip_call_to=dial_info["phone_number"],
                participant_identity=participant_identity,
                wait_until_answered=True,
            )
        )
        participant = await ctx.wait_for_participant(identity=participant_identity)
        logger.info(f"participant joined: {participant.identity}")
        agent.set_participant(participant)
        
        await session.start(
            agent=agent,
            room=ctx.room,
            room_options=room_io.RoomOptions(
                participant_identity=participant_identity,  # Wait for phone participant
            ),
        )
    except api.TwirpError as e:
            logger.error(
                f"error creating SIP participant: {e.message}, "
                f"SIP status: {e.metadata.get('sip_status_code')} "
                f"{e.metadata.get('sip_status')}"
            )
            ctx.shutdown()

if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name="RealEstate-Outbound-Agent"
        )
    )
