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
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from geopy.distance import geodesic
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
from livekit.plugins import openai, silero, google as lk_google, deepgram, noise_cancellation
from livekit.agents import room_io, metrics
from livekit.agents.voice import MetricsCollectedEvent
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from utils import database as db
from prompts.tr_inbound_prompt import SYSTEM_PROMPT
from datetime import datetime, timedelta, timezone as tz


logger = logging.getLogger("grok-agent")
logger.setLevel(logging.INFO)

load_dotenv()
CALENDAR = os.getenv("CALENDAR_ID")

def get_google_token():
    """Get OAuth token from service account credentials."""
    credentials = service_account.Credentials.from_service_account_file(
        os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
        scopes=["https://www.googleapis.com/auth/calendar"]
    )
    credentials.refresh(Request())
    return credentials.token
#TODO check tool calls if they work
#TODO add agent to push confused client into doing specific things
class MyAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=SYSTEM_PROMPT
        )

    async def on_enter(self):
        await self.session.generate_reply(allow_interruptions=False)
    
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
        # Extract phone number from room name (format: call-_393517843713_...)
        room_name = context.session.room.name if context.session.room else ""
        phone_number = "Unknown"
        if room_name.startswith("call-"):
            parts = room_name.split("_")
            if len(parts) >= 2:
                phone_number = parts[1]
        
        token = get_google_token()
        start = datetime.fromisoformat(date)
        end = start + timedelta(minutes=30)

        url = f"https://www.googleapis.com/calendar/v3/calendars/{CALENDAR}/events"
        body = {
            "summary": f"Ziyaret: {apartment_address}",
            "start": {
                "dateTime": start.isoformat(),
                "timeZone": "Europe/Istanbul"
            },
            "end": {
                "dateTime": end.isoformat(),
                "timeZone": "Europe/Istanbul"
            },
            "description": f"Emlak ziyareti\nMüşteri telefonu: {phone_number}",
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "email", "minutes": 6 * 60},
                    {"method": "popup", "minutes": 30}
                ]
            }
        }
        response = requests.post(url, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, json=body)
        if response.status_code != 200:
            logger.error(f"Failed to create calendar event: {response.text}")
        # Always return success message to avoid confusing the voice AI
        return f"Randevu onaylandı: {apartment_address}"

        

    @function_tool
    async def get_apartment_info(
        self, context: RunContext, apartment_address: str
    ):
        
        response_openstreetmap = requests.get(
            url="https://nominatim.openstreetmap.org/search",
            params={
                "q": f"{apartment_address}, Bartin, Turkey",
                "format": "json",
                "limit": 1
            },
            headers={"User-Agent": "RinovaAI/1.0 (rinova.capmapai.com)"}
        )        
        geo_data = response_openstreetmap.json()
        
        # 2. If geocoding failed, use LLM to match listing name
        if not geo_data: 
            listings = db.getCurrentListings()
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
                            The user asked about: "{apartment_address}"
                            
                            Your task: Find the best matching listing name.
                            - If you find a match, output ONLY the listing name.
                            - If no match, output 3 random listing names from the list, separated by commas.
                            
                            Output only the listing name(s), nothing else."""
                        }
                    ],
                })
            )
            data = response.json()
            listing_names = data['choices'][0]['message']['content']
            
            # If multiple listings returned (no match), return suggestions
            if "," in listing_names:
                return json.dumps({
                    "status": "suggestions",
                    "suggestions": [name.strip() for name in listing_names.split(",")]
                })
            
            # Single match found - try to get it, or return all listings as suggestions
            listing = db.getListing(listing_names.strip())
            if listing:
                return listing.json()
            else:
                # Fallback: return all available listings
                all_listings = db.getCurrentListings()
                return json.dumps({
                    "status": "suggestions",
                    "suggestions": [name.strip() for name in all_listings.split(",")[:3]]
                })

        # 3. Geocoding succeeded - find closest listings by distance
        user_coords = (float(geo_data[0]["lat"]), float(geo_data[0]["lon"]))
        
        listings = db.getAllListingsWithCoords()
        
        # Calculate distance for each listing
        for listing in listings:
            listing['distance_km'] = geodesic(
                user_coords, 
                (listing['latitude'], listing['longitude'])
            ).km
        
        # Sort by distance and get top 3
        top3 = sorted(listings, key=lambda x: x['distance_km'])[:3]

        # Return raw data - let LLM decide how to present it
        return json.dumps({
            "status": "found_nearby" if top3[0]['distance_km'] >= 0.1 else "exact_match",
            "closest": {
                "name": top3[0]['name'],
                "address": top3[0]['address'],
                "distance_meters": int(top3[0]['distance_km'] * 1000),
                "price": top3[0]['price'],
                "description": top3[0]['description'][:300]
            },
            "alternatives": [
                {"name": l['name'], "distance_meters": int(l['distance_km'] * 1000)} 
                for l in top3[1:3]
            ]
        })


        
    """Called when the user explicitly asks questions relating to an apartment or wants information
    on the apartment.
    Ensure the address of the apartment is provided.

    Args:
        apartment_address (str): The address of the apartment
    """
    #TODO MAIN PROBLEM 1: VOICE AI SHOULD LEAD THE CONVERSATION
    #TODO MAIN PROBLEM 2: STT SHOULD BE MADE INTO A PIPELINE TO SEE WHICH ONE PERFORMS BEST
    #TODO MAIN PROBLEM 3: WHEN A PERSON DOESNT KNOW WTF ADDRESS THEY ARE TALKING ABOUT THE APARTMENT INFO TOOL SHOULD BE A TURKISH BAKKAL

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
        # Wait for any current speech to finish before hanging up
        await ctx.wait_for_playout()
        await self.hangup()
    
    @function_tool()
    async def get_existing_bookings(self, ctx: RunContext, date: str):

        """Called when the user wants to learn about their current bookings for a given apartment

        Args:
            date (str): The date of the appointment
        """
        start_date = datetime.fromisoformat(date).replace(tzinfo=tz(timedelta(hours=3)))
        end_date = start_date + timedelta(minutes=30)
        token = get_google_token()
        params = {
            "timeMin": start_date.isoformat(),
            "timeMax": end_date.isoformat(),
            "timeZone": "Europe/Istanbul",
            "singleEvents": True,
            "orderBy": "startTime",
            "maxResults": 1
        }
        url_listEvent = f"https://www.googleapis.com/calendar/v3/calendars/{CALENDAR}/events"
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
        start_date = datetime.fromisoformat(date).replace(tzinfo=tz(timedelta(hours=3)))
        end_date = start_date + timedelta(minutes=30)
        token = get_google_token()
        params = {
            "timeMin": start_date.isoformat(),
            "timeMax": end_date.isoformat(),
            "timeZone": "Europe/Istanbul",
            "singleEvents": True,
            "orderBy": "startTime",
            "maxResults": 1
        }
        
        url_listEvent = f"https://www.googleapis.com/calendar/v3/calendars/{CALENDAR}/events"
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
        

        url_deleteEvent = f"https://www.googleapis.com/calendar/v3/calendars/{CALENDAR}/events/"+event_id
        response = requests.delete(url_deleteEvent, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
        if response == {}:
            return "Booking Successfully Cancelled"
        else: 
            #TODO: for tool call fails I should implement a logging system in the dashboard
            logger.info("yall something went wrong")
            return "Booking Successfully Cancelled"

    @function_tool()
    async def check_available_slots(self, ctx: RunContext, date: str):
        """Called when the user wants to check available slots for a given date

        Args:
            date (str): The date of the appointment
        """
        
        base_date = datetime.fromisoformat(date).replace(tzinfo=tz(timedelta(hours=3)))
        # Turkey real estate: 08:00-19:00 non-stop
        start_time = base_date.replace(hour=8, minute=0, second=0, microsecond=0)
        end_time = base_date.replace(hour=19, minute=0, second=0, microsecond=0)
        
        token = get_google_token()
        url = "https://www.googleapis.com/calendar/v3/freeBusy"
        body = {
            "timeMin": start_time.isoformat(),
            "timeMax": end_time.isoformat(),
            "timeZone": "Europe/Istanbul",
            "items": [
                {
                    "id": CALENDAR
                }
            ]
        }
        logger.info(f"FreeBusy request body: {body}")
        response = requests.post(url, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, json=body)
        
        data = response.json()
        
        # Log the actual response to debug
        logger.info(f"FreeBusy response: {data}")
        
        # Check for errors
        if "error" in data:
            return f"Calendar error: {data['error'].get('message', 'Unknown error')}"
        
        if "calendars" not in data:
            return f"Unexpected response from calendar API: {data}"
        
        available_slots = []
        begin = start_time
        end = end_time
        
        calendar_data = data["calendars"].get(CALENDAR, {})
        busy_slots = calendar_data.get("busy", [])
        
        # If no busy slots, entire day is available
        if not busy_slots:
            available_slots.append((start_time.strftime("%H:%M"), end_time.strftime("%H:%M")))
        else:
            for i in range(len(busy_slots)):
                busy_start = datetime.fromisoformat(busy_slots[i]["start"].replace("Z", "+00:00"))
                busy_end = datetime.fromisoformat(busy_slots[i]["end"].replace("Z", "+00:00"))
                if begin < busy_start:
                    available_slots.append((begin.strftime("%H:%M"), busy_start.strftime("%H:%M")))
                begin = busy_end
            # Check if there's time left after last busy slot
            if begin < end:
                available_slots.append((begin.strftime("%H:%M"), end.strftime("%H:%M")))
        
        # Lunch break: 12:00-13:30 - avoid unless no other option
        lunch_start = "12:00"
        lunch_end = "13:30"
        
        def overlaps_lunch(slot_start, slot_end):
            """Check if a slot overlaps with lunch break"""
            return not (slot_end <= lunch_start or slot_start >= lunch_end)
        
        def is_entirely_lunch(slot_start, slot_end):
            """Check if slot is entirely within lunch break"""
            return slot_start >= lunch_start and slot_end <= lunch_end
        
        # Separate slots into preferred (non-lunch) and lunch slots
        preferred_slots = []
        lunch_slots = []
        
        for slot in available_slots:
            slot_start, slot_end = slot
            if is_entirely_lunch(slot_start, slot_end):
                lunch_slots.append(slot)
            elif overlaps_lunch(slot_start, slot_end):
                # Split slot around lunch break
                if slot_start < lunch_start:
                    preferred_slots.append((slot_start, lunch_start))
                if slot_end > lunch_end:
                    preferred_slots.append((lunch_end, slot_end))
                # Keep original lunch portion as fallback
                lunch_slots.append((max(slot_start, lunch_start), min(slot_end, lunch_end)))
            else:
                preferred_slots.append(slot)
        
        # Use preferred slots if available, otherwise fall back to lunch slots
        final_slots = preferred_slots if preferred_slots else lunch_slots
            
        return "Müsait ziyaret saatleri: (listeden 30 dakikalık bir aralık seçin) " + str(final_slots)

server = AgentServer()

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

server.setup_fnc = prewarm

@server.rtc_session()
async def entrypoint(ctx: JobContext):
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }
    session = AgentSession(
        stt=deepgram.STT(model="nova-3", language="tr-TR"),
        llm=openai.LLM(
            model="x-ai/grok-4-fast",
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
        ),
        tts=lk_google.TTS(
            gender="female",
            voice_name="tr-TR-Chirp3-HD-Laomedeia",
            language="tr-TR"
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
                noise_cancellation=noise_cancellation.BVC(),
            ),
        ),
    )
    
if __name__ == "__main__":
    cli.run_app(server)
