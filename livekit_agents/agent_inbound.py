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

from dotenv import load_dotenv
from pydantic import BaseModel
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    ChatContext,
    FunctionTool,
    JobContext,
    ModelSettings,
    RunContext,
    cli,
    function_tool,
    JobProcess
)
from livekit.plugins import openai,silero
from system_prompt import SYSTEM_PROMPT
import database as db
from datetime import datetime, timedelta


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
        #TODO this token might not be implemented, well I'm not sure entirely how I will go about 
        #our voiceai system I might keep our old dashboard, I guess I need to give inbound
        #ah fk it go on
        token = get_google_token()
        start = datetime.fromisoformat(date)
        end = start + timedelta(minutes=30)

        url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
        body = {
            "summary": f"{apartment_address} appuntamento {date}",
            "start": {
                "dateTime": start.isoformat(),
                "timeZone": "Europe/Rome"
            },
            "end": {
                "dateTime": end.isoformat(),
                "timeZone": "Europe/Rome"
            },
            "description": "Visita",
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "email", "minutes": 6 * 60},
                    {"method": "popup", "minutes": 30}
                ]
            }
        }
        response = requests.post(url, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, json=body)
        

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
                "Authorization": "Bearer " + os.getenv("OPENROUTER_API_KEY"),
                "HTTP-Referer": "https://rinova.capmapai.com",
                "X-Title": "Rinova AI",
            },
            data=json.dumps({
                "model": "google/gemini-3-flash-preview",
                "messages": [
                    {
                        "role": "user",
                        "content": f"""You are AItaxonomy, a real estate mapping assistant.
                        You have these listings: {listings}
                        your task is to map the listing that the user specified here with the 
                        appropriate listing name, since the user might have given an incomplete/half-incorrect address, this is the address they gave: " 
                        {apartment_address} Output which listing name it is, and nothing else, if you find no matches, output 'None'"""
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
        start_date = datetime.fromisoformat(date)
        end_date = start_date + timedelta(minutes=30)
        token = get_google_token()
        params = {
            "timeMin": start_date.isoformat(),
            "timeMax": end_date.isoformat(),
            "singleEvents": True,
            "orderBy": "startTime",
            "maxResults": 1
        }
        url_listEvent = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
        response_listEvent = requests.get(url_listEvent, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, params=params)
        data = response_listEvent.json()
        event_summaries = []
        event_times = []
        if data["items"] == []:
            return "No events found on this time"
        for events in data["items"]:
            if datetime.fromisoformat(events["start"]["dateTime"]).replace(tzinfo=None) == start_date.replace(tzinfo=None):
                event_summaries.append(events["summary"])
                event_times.append(events["start"]["dateTime"])
        for i in range(len(event_summaries)):
            event_summaries[i] = event_summaries[i] + " at " + event_times[i]
        return "all events on this time: " + (", ").join(event_summaries)   



    @function_tool()
    async def cancel_booking(self, ctx: RunContext, date: str):
        """Called when the user wants to cancel a booking for a given apartment

        Args:
            date (str): The date of the appointment
        """
        start_date = datetime.fromisoformat(date)
        end_date = start_date + timedelta(minutes=30)
        token = get_google_token()
        params = {
            "timeMin": start_date.isoformat(),
            "timeMax": end_date.isoformat(),
            "singleEvents": True,
            "orderBy": "startTime",
            "maxResults": 1
        }
        url_listEvent = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
        response_listEvent = requests.get(url_listEvent, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, params=params)
        data = response_listEvent.json()
        event_id = None
        if data["items"] == []:
            return "Booking Successfully Cancelled"
        for events in data["items"]:
            if datetime.fromisoformat(events["start"]["dateTime"]).replace(tzinfo=None) == start_date.replace(tzinfo=None):
                event_id = events["id"]
        if event_id == None:
            return "Booking Successfully Cancelled"
        

        url_deleteEvent = "https://www.googleapis.com/calendar/v3/calendars/primary/events/"+event_id
        response = requests.delete(url_deleteEvent, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
        if response == {}:
            return "Booking Successfully Cancelled"
        else: 
            #TODO: for tool call fails I should implement a logging system in the dashboard
            console.log("yall something went wrong")
            return "Booking Successfully Cancelled"

    @function_tool()
    async def check_available_slots(self, ctx: RunContext, date: str):
        """Called when the user wants to check available slots for a given date

        Args:
            date (str): The date of the appointment
        """
        start_10 = datetime.fromisoformat(date).replace(hour=10, minute=0, second=0, microsecond=0)
        end_1230 = datetime.fromisoformat(date).replace(hour=12, minute=30, second=0, microsecond=0)
        start_15 = datetime.fromisoformat(date).replace(hour=15, minute=0, second=0, microsecond=0)
        end_19 = datetime.fromisoformat(date).replace(hour=19, minute=0, second=0, microsecond=0)
        
        
        token = get_google_token()
        url = "https://www.googleapis.com/calendar/v3/freeBusy"
        body = {
            "timeMin": start_10.isoformat(),
            "timeMax": end_1230.isoformat(),
            "items": [
                {
                    "id": "primary"
                }
            ]
        }
        response_morning = requests.post(url, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, json=body)
        
        token = get_google_token()
        body = {
            "timeMin": start_15.isoformat(),
            "timeMax": end_19.isoformat(),
            "items": [
                {
                    "id": "primary"
                }
            ]
        }
        response_afternoon = requests.post(url, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, json=body)
        
        data_morning = response_morning.json()
        data_afternoon = response_afternoon.json()
        available_slots = []
        begin = datetime.fromisoformat(date).replace(hour=10, minute=0, second=0, microsecond=0)
        end = datetime.fromisoformat(date).replace(hour=12, minute=30, second=0, microsecond=0)
        for i in range(len(data_morning["calendars"]["primary"]["busy"])):
            busy_start = data_morning["calendars"]["primary"]["busy"][i]["start"]
            busy_end = data_morning["calendars"]["primary"]["busy"][i]["end"]
            if end <= busy_end:
                break
            if begin < busy_start:
                available_slots.append((begin, busy_start))
            #elif begin == busy_start:
            #    begin = busy_end
            #    end = begin + timedelta(minutes=30)    
            #else:
            #    continue    
            begin = busy_end
            

        begin = datetime.fromisoformat(date).replace(hour=15, minute=0, second=0, microsecond=0)
        end = datetime.fromisoformat(date).replace(hour=19, minute=0, second=0, microsecond=0)
        for i in range(len(data_afternoon["calendars"]["primary"]["busy"])):
            busy_start = data_afternoon["calendars"]["primary"]["busy"][i]["start"]
            busy_end = data_afternoon["calendars"]["primary"]["busy"][i]["end"]
            if end <= busy_end:
                break
            if begin < busy_start:
                available_slots.append((begin, busy_start))
            #elif begin == busy_start:
            #    begin = busy_end
            #    end = begin + timedelta(minutes=30)    
            #else:
            #    continue    
            begin = busy_end
            
        return "Here are the available slots, lead them to the earliest one if it works with the customer, otherwise tell them a time that works for them: " + str(available_slots) + " if there was no available slots you will see nothing here."

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
    
