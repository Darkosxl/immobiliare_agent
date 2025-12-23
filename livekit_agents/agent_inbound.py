from crawl4ai import (
    AdaptiveConfig,
    AdaptiveCrawler,
    AsyncWebCrawler,
    BrowserConfig,
    CacheMode,
    CrawlerRunConfig,
    LLMConfig,
    VirtualScrollConfig,
    JsonCssExtractionStrategy
)
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
        self, context: RunContext, apartment_address: str, date: str
    ):
    """Called when the user wants to book an appointment/visit or a tour of the apartment
    Ensure the address of the apartment and the date are provided.

    Args:
        apartment_address (str): The address of the apartment
        date (str): The date of the appointment
        
    """

    

    @function_tool
    async def get_apartment_info(
        self, context: RunContext, apartment_address: str
    ):
        #TODO write database function to fetch current listings given an agency name
        #TODO write a database with columns: description, address, price, link, real_Estate_agency
        
        listings = db.getCurrentListings(Real_Estate_Agency=agency)
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": : "Bearer " + os.getenv("OPENROUTER_API_KEY"),
                "HTTP-Referer": "https://rinova.capmapai.com",
                "X-Title": "Rinova AI",
            },
            data=json.dumps({
                "model": "google/gemini-3-flash-preview",
                "messages": [
                    {
                        "role": "user",
                        "content": "You are AItaxonomy, a real estate mapping assistant. \
                        You have these listings: " + listings + "\ \
                        your task is to map the listing that the user specified here with the \
                        appropriate listing name, since the user might have given an incomplete/half-incorrect address, this is the address they gave: " \
                        + apartment_address + " Output which listing name it is, and nothing else, if you find no matches, output 'None'"
                    }
                ],
            })
        )

        data = response.json()
        listing_name = data['message']['content']
        #TODO implement this function)
        listing = db.getListing(listing_name)
        listing_json = listing.json()
        
        #TODO OPTIONAL: json might be the best might not be the best you can investigate
        return listing_json

    """Called when the user explicitly asks questions relating to an apartment or wants information
    on the apartment.
    Ensure the address of the apartment is provided.

    Args:
        apartment_address (str): The address of the apartment
    """


    #    idealista_browser_conf = BrowserConfig(
    #        headless=False,
    #        verbose=True,
    #        proxy_confg=os.getenv("PROXY_API_KEY"),
    #        text_mode=False
    #    )

    #    async with AsyncWebCrawler(config=browser_conf) as idealistacrawler:
    #        run_config = CrawlerRunConfig(
    #            excluded_tags=["img", "video", "source", "picture", "iframe", "svg"],
    #        )

    #TODO IMPLEMENT ALL GOOGLE TOOL CALLS HERE
    @function_tool 
    async def end_call(self, ctx: RunContext):
        """Called when the user wants to end the call"""
        logger.info(f"ending the call")
        current_speech = ctx.session.current_speech
        if current_spech:
            await current_speech.wait_for_playout()
        
        await self.hangup()
    
    @function_tool()
    async def get_existing_bookings(self, ctx: RunContext, date: str):

        """Called when the user wants to learn about their current bookings for a given apartment

        Args:
            date (str): The date of the appointment
        """
    @function_tool()
    async def cancel_booking(self, ctx: RunContext, date: str):
        """Called when the user wants to cancel a booking for a given apartment

        Args:
            date (str): The date of the appointment
        """
    @function_tool()
    async def check_available_slots(self, ctx: RunContext, date: str):
        """Called when the user wants to check available slots for a given date

        Args:
            date (str): The date of the appointment
        """
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

    usage_collector = metrics.UsageCollector()
    @session.on("metrics_collected")
    def on_metrics(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)
    
    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"Usage: {summary}")
    ctx.add_shutdown_callback(log_usage)
    #TODO THE CHAT ROOM SHOULD BE FROM OUR FLYNUMBER, MAKE SURE THAT WORKS AND
    # UNDERSTAND DEEPLY HOW IT DOES
    await session.start(
        agent=MyAgent(),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                #noise_cancellation=noise_cancellation.BVC(),
            ),
        ),
    )
    
