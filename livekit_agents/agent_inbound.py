import crawl4ai
import logging
import random
from enum import Enum
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    ChatContext,
    FunctionTool,
    JobCOntext,
    ModelSettings,
    cli,
    function_tool
)
from livekit.plugins import openai,silero
from system_prompt.py import SYSTEM_PROMPT

logger = logging.getLogger("grok-agent")
logger.setLevel(logging.INFO)

load_dotenv()

class MyAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=SYSTEM_PROMPT
        )

    async def on_enter(self):
        self.session.generate_reply(allow_interruptions=False)
    
    @function_tool
    async def schedule_meeting(
        self, context: RunContext, street_address: str, date: str
    ):
        


    @function_tool
    async def scrape_idealista(
        url: str
    ):

server = AgentServer()

def prewarm(porc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

server.setup_fnc = prewarm

@server.rtc_session()
async def entrypoint(ctx: JobContext):
    ctx.log_context_fields = {
        "room": ctx.room_name,
    }
    session = AgentSession(
        stt="deepgram/nova-3",
        llm="openrouter/x-ai/grok-4-fast",
        tts=google.TTS(
            gender="female",
            voice_name="it-IT-Chirp3-HD-Achernar",
            language="it-IT"
        ),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
        resume_false_interruption=True,
        false_interruption_timeout=1.0,
    )

    usage_collector = metrics.
