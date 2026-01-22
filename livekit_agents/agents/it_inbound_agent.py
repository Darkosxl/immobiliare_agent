#from crawl4ai import (
#    AdaptiveConfig,
#    AdaptiveCrawler,
#    AsyncWebCrawler,
#    BrowserConfig,
#    CacheMode,
#    CrawlerRunConfig,
#    LLMConfig,
#    VirtualScrollConfig,
#    JsonCssExtractionStrategy
#)
import logging
import random
from enum import Enum
from typing import Literal
import os
import json
import requests
import google.auth
from groq import Groq
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from geopy.distance import geodesic
from dotenv import load_dotenv
from pydantic import BaseModel 
from livekit import api
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    inference,
    ChatContext,
    get_job_context,
    FunctionTool,
    JobContext,
    ModelSettings,
    RunContext,
    cli,
    function_tool,
    JobProcess,
    WorkerOptions
)
from livekit.plugins import groq
from livekit.plugins import openai, silero, google as lk_google, deepgram, noise_cancellation, elevenlabs
from livekit.agents import room_io, metrics
from livekit.agents.voice import MetricsCollectedEvent
from livekit.plugins.turn_detector.multilingual import MultilingualModel
import utils.database as db
from prompts.it_inbound_prompt import SYSTEM_PROMPT, immobiliare_agenzia
from datetime import datetime, timedelta, timezone as tz
from utils.agents_utils import get_google_token
from tools.real_estate_tools import get_apartment_info
from tools.calendar_tools import (
    schedule_meeting,
    end_call,
    get_existing_bookings,
    cancel_booking,
    check_available_slots
)
import tempfile

logger = logging.getLogger("grok-agent")
logger.setLevel(logging.INFO)
load_dotenv(".env")
CALENDAR = os.getenv("CALENDAR_ID")


class RealEstateItalianAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=SYSTEM_PROMPT,
            tools=[
                get_apartment_info,
                schedule_meeting,
                end_call,
                get_existing_bookings,
                cancel_booking,
                check_available_slots
            ]
        )

    
    async def on_enter(self):
        #TODO PROPER SPAM CALL CHECK
        #if not await self._check_whitelisted():
        #    await self.session.generate_reply(instructions="let the other person know that you are hanging up because their number is not whitelisted", allow_interruptions=False)
        #    #await self.session.wait_for_playout()
        #    await self.hangup()
        #    return
        await self.session.generate_reply(allow_interruptions=False)

    async def hangup(self):
        job_ctx = get_job_context()
        try:
            await job_ctx.api.room.delete_room(
                api.DeleteRoomRequest(
                    room=job_ctx.room.name,
                )
            )
        except Exception as e:
            logger.warning(f"Could not delete room (may already be deleted): {e}")
    async def _check_whitelisted(self) -> bool:
        """Check if caller is whitelisted using the database"""
        job_ctx = get_job_context()
        room_name = job_ctx.room.name if job_ctx.room else ""
        phone_number = "Unknown"
        
        if room_name.startswith("call-"):
            parts = room_name.split("_")
            if len(parts) >= 2:
                phone_number = parts[1]
        
        # If no whitelist entries exist, allow all (not configured)
        all_whitelisted = db.get_all_whitelisted()
        if not all_whitelisted:
            return True
        
        return db.is_whitelisted(phone_number)

server = AgentServer()

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

@server.rtc_session()
async def entrypoint(ctx: JobContext):
    voice_settings = elevenlabs.VoiceSettings(
        speed=1.11,
        stability=0.76,
        style=0.5,
        similarity_boost=0.5
    )
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }
    session = AgentSession(
        stt=deepgram.STT(model="nova-3", language="it-IT"),
        #llm=openai.LLM.with_x_ai(
        #   model="grok-4-fast-reasoning",
        #)
        llm=openai.LLM(
            model="gpt-5.2-chat-latest",
            api_key=os.getenv("OPENAI_API_KEY")
        ),
        #lk_google.LLM(
        #    model="gemini-2.5-flash",
        #    vertexai=True,
            #project="ancient-medium-454210-i1",
            #location="us-central1"
        tts=elevenlabs.TTS(
            voice_id="gfKKsLN1k0oYYN9n2dXX",#violetta
            model="eleven_multilingual_v2",
            api_key=os.getenv("ELEVENLABS_API_KEY"),
            voice_settings=voice_settings
        )
        #lk_google.TTS(
        #    gender="female",
        #    voice_name="it-IT-Chirp3-HD-Achernar",
        #    language="it-IT"
        #)
        ,
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
        resume_false_interruption=True,
        false_interruption_timeout=1.0,
    )

    usage_collector = metrics.UsageCollector()
    @session.on("metrics_collected")
    def on_metrics(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)
    
    @session.on("function_calls_finished")
    def on_tool_result(ev):
        for call in ev.function_calls:
            logger.info(f"🔧 Tool: {call.name} | Result: {call.result}")
    
    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"Usage: {summary}")
    ctx.add_shutdown_callback(log_usage)
    #TODO THE CHAT ROOM SHOULD BE FROM OUR FLYNUMBER, MAKE SURE THAT WORKS AND
    # UNDERSTAND DEEPLY HOW IT DOES
    await session.start(
        agent=RealEstateItalianAgent(),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=noise_cancellation.BVC(),
            ),
        ),
    )
    
if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
            agent_name="RealEstate-Inbound-Agent"
        )
    )
