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
    ChatContext,
    get_job_context,
    FunctionTool,
    JobContext,
    ModelSettings,
    RunContext,
    cli,
    function_tool,
    JobProcess
)
from livekit.plugins import groq
from livekit.plugins import openai, silero, google as lk_google, deepgram, noise_cancellation
from livekit.agents import room_io, metrics
from livekit.agents.voice import MetricsCollectedEvent
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from tools import database as db
from prompts.it_inbound_prompt import SYSTEM_PROMPT, immobiliare_agenzia
from datetime import datetime, timedelta, timezone as tz
import tempfile

logger = logging.getLogger("grok-agent")
logger.setLevel(logging.INFO)
load_dotenv(".env")
CALENDAR = os.getenv("CALENDAR_ID")

#write the json to a temp file
_google_creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
if _google_creds.strip().startswith("{"):
    _creds_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
    _creds_file.write(_google_creds)
    _creds_file.close()
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = _creds_file.name
    logger.info(f"Wrote Google credentials to temp file: {_creds_file.name}")

def get_google_token():
    """Get OAuth token from service account credentials.
    
    GOOGLE_APPLICATION_CREDENTIALS can be either:
    - A file path to the JSON file
    - The raw JSON string (for environments where you can't mount files)
    """
    creds_value = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    scopes = ["https://www.googleapis.com/auth/calendar"]
    
    try:
        creds_info = json.loads(creds_value)
        credentials = service_account.Credentials.from_service_account_info(
            creds_info, scopes=scopes
        )
    except (json.JSONDecodeError, TypeError):
        credentials = service_account.Credentials.from_service_account_file(
            creds_value, scopes=scopes
        )
    
    credentials.refresh(Request())
    return credentials.token

class RealEstateItalianAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=SYSTEM_PROMPT
        )

    
    async def on_enter(self):
        #TODO PROPER SPAM CALL CHECK
        if not await self._check_whitelisted():
            await self.session.generate_reply(instructions="let the other person know that you are hanging up because their number is not whitelisted", allow_interruptions=False)
            #await self.session.wait_for_playout()
            await self.hangup()
            return
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
        logger.info(f"🚀 TOOL: schedule_meeting | address={apartment_address}, date={date}")
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
            "summary": f"Visita: {apartment_address}",
            "start": {
                "dateTime": start.isoformat(),
                "timeZone": "Europe/Rome"
            },
            "end": {
                "dateTime": end.isoformat(),
                "timeZone": "Europe/Rome"
            },
            "description": f"Visita immobile\nTelefono cliente: {phone_number}",
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
        result = f"Appuntamento confermato per {apartment_address}"
        logger.info(f"✅ TOOL RESULT: schedule_meeting | {result}")
        return result

        

    @function_tool
    async def get_apartment_info(
        self, context: RunContext,
        query: str
    ):
        """Search for apartments based on the caller's requirements.
        
        Args:
            query: Natural language description of what the caller is looking for.
                   Include ALL relevant context: buyer or renter, residential or commercial,
                   zone/neighborhood/address, budget, number of rooms, any other preferences.
                   Example: "Cliente vuole comprare appartamento residenziale zona Porta Romana, budget 200mila euro, 2-3 camere"
        """
        
        logger.info(f"🚀🚀🚀 TOOL CALLED: get_apartment_info with query: {query}")
        
        # Speak a filler phrase while processing (chosen randomly for variation)
        filler_phrases = [
            "Verifico subito.",
            "Controllo i dati.",
            "Un attimo, cerco le informazioni.",
            "Vediamo cosa abbiamo.",
        ]
        await context.session.generate_reply(
            instructions=f"Say exactly this and nothing else: {random.choice(filler_phrases)}",
            allow_interruptions=False
        )
        
        # Step 1: Use a smart LLM to extract structured parameters from the query
        client = Groq()
        extraction = client.chat.completions.create(
            model="moonshotai/kimi-k2-instruct-0905",  # Smart model for extraction
            messages=[{
                "role": "user",
                "content": f"""Extract search parameters from this real estate query. Output ONLY valid JSON, nothing else.

                Query: "{query}"

                Extract these fields (use null if not mentioned):
                - zone: string (neighborhood, area, or address)
                - listing_type: "sale" or "rent"  
                - property_type: "living" or "commercial"
                - budget: integer (in euros, convert "200mila" to 200000)
                - rooms: integer (number of rooms/bedrooms)

                JSON output:"""
            }],
            temperature=0,
            max_completion_tokens=600
        )
        
        try:
            params = json.loads(extraction.choices[0].message.content.strip())
        except json.JSONDecodeError:
            # Fallback: just use the query as zone
            params = {"zone": query, "listing_type": "rent", "property_type": "living", "budget": None, "rooms": None}
        
        logger.info(f"🔍 Extracted params: {params}")
        
        zone = params.get("zone")
        budget = params.get("budget")
        
        # Step 2: If no zone provided, return suggestions based on other filters
        if not zone:
            listings = db.getAllListingsWithCoords()
            
            if budget:
                listings = [l for l in listings if l.get('price', 0) <= budget]
            
            if not listings:
                listings = db.getAllListingsWithCoords()[:5]
            else:
                listings = listings[:5]
            
            return json.dumps({
                "status": "suggestions",
                "message": "Ecco alcune proposte",
                "listings": [
                    {
                        "name": l['name'],
                        "address": l['address'],
                        "price": l['price'],
                        "rooms": l.get('rooms', 'N/A'),
                        "description": l.get('description', '')[:150]
                    } for l in listings
                ]
            })
        
        # Step 3: Zone provided - try geocoding
        response_openstreetmap = requests.get(
            url="https://nominatim.openstreetmap.org/search",
            params={
                "q": f"{zone}, Milano, Italia",
                "format": "json",
                "limit": 1
            },
            headers={"User-Agent": "RinovaAI/1.0 (rinova.capmapai.com)"}
        )        
        geo_data = response_openstreetmap.json()
        
        # Step 3a: Geocoding failed - use LLM to match listing name
        if not geo_data: 
            listings = db.getCurrentListings(
                Real_Estate_Agency=immobiliare_agenzia, 
                property_type=params.get("property_type", "living"), 
                listing_type=params.get("listing_type", "rent")
            )
            client = Groq()
            completion = client.chat.completions.create(
                model="moonshotai/kimi-k2-instruct-0905",
                messages=[
                {
                    "role": "user",
                    "content": f"""You are a real estate matching assistant.
Available listings: {listings}
User is looking for: "{zone}"

Find the best matching listing name.
- If you find a match, output ONLY the listing name.
- If no match, output 3 listing names from the list, separated by commas.

Output only the listing name(s), nothing else."""
                }],
                temperature=0.1,
                max_completion_tokens=1000
            )
            
            listing_names = completion.choices[0].message.content
            
            # If multiple listings returned (no match), return suggestions
            if "," in listing_names:
                return json.dumps({
                    "status": "suggestions",
                    "suggestions": [name.strip() for name in listing_names.split(",")]
                })
            
            # Single match found
            listing = db.getListing(listing_names.strip())
            if listing:
                return listing.json()
            else:
                all_listings = db.getCurrentListings()
                return json.dumps({
                    "status": "suggestions",
                    "suggestions": [name.strip() for name in all_listings.split(",")[:3]]
                })

        # Step 4: Geocoding succeeded - find closest listings by distance
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

   
    @function_tool 
    async def end_call(self, ctx: RunContext, reason: str = "user_requested"):
        """Called when the user wants to end the call
        
        Args:
            reason: Why the call is ending (optional, defaults to user_requested)
        """
        logger.info(f"🚀 TOOL: end_call | reason={reason}")
        await ctx.wait_for_playout()
        await self.hangup()
        logger.info(f"✅ TOOL RESULT: end_call | call ended")
    
            
            
    @function_tool()
    async def get_existing_bookings(self, ctx: RunContext, date: str):

        """Called when the user wants to learn about their current bookings for a given apartment

        Args:
            date (str): The date of the appointment
        """
        logger.info(f"🚀 TOOL: get_existing_bookings | date={date}")
        start_date = datetime.fromisoformat(date).replace(tzinfo=tz(timedelta(hours=1)))
        end_date = start_date + timedelta(minutes=30)
        token = get_google_token()
        params = {
            "timeMin": start_date.isoformat(),
            "timeMax": end_date.isoformat(),
            "timeZone": "Europe/Rome",
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
        result = "all events on this time: " + (", ").join(event_summaries)
        logger.info(f"✅ TOOL RESULT: get_existing_bookings | {result}")
        return result



    @function_tool()
    async def cancel_booking(self, ctx: RunContext, date: str):
        """Called when the user wants to cancel a booking for a given apartment

        Args:
            date (str): The date of the appointment
        """
        logger.info(f"🚀 TOOL: cancel_booking | date={date}")
        start_date = datetime.fromisoformat(date).replace(tzinfo=tz(timedelta(hours=1)))
        end_date = start_date + timedelta(minutes=30)
        token = get_google_token()
        params = {
            "timeMin": start_date.isoformat(),
            "timeMax": end_date.isoformat(),
            "timeZone": "Europe/Rome",
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
        logger.info(f"🚀 TOOL: check_available_slots | date={date}")
        base_date = datetime.fromisoformat(date).replace(tzinfo=tz(timedelta(hours=1)))
        start_10 = base_date.replace(hour=10, minute=0, second=0, microsecond=0)
        end_1230 = base_date.replace(hour=12, minute=30, second=0, microsecond=0)
        start_15 = base_date.replace(hour=15, minute=0, second=0, microsecond=0)
        end_19 = base_date.replace(hour=19, minute=0, second=0, microsecond=0)
        
        token = get_google_token()
        url = "https://www.googleapis.com/calendar/v3/freeBusy"
        body = {
            "timeMin": start_10.isoformat(),
            "timeMax": end_1230.isoformat(),
            "timeZone": "Europe/Rome",
            "items": [
                {
                    "id": CALENDAR
                }
            ]
        }
        logger.info(f"FreeBusy request body (morning): {body}")
        response_morning = requests.post(url, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, json=body)
        
        token = get_google_token()
        body = {
            "timeMin": start_15.isoformat(),
            "timeMax": end_19.isoformat(),
            "timeZone": "Europe/Rome",
            "items": [
                {
                    "id": CALENDAR
                }
            ]
        }
        response_afternoon = requests.post(url, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, json=body)
        
        data_morning = response_morning.json()
        data_afternoon = response_afternoon.json()
        
        # Log the actual response to debug
        logger.info(f"FreeBusy morning response: {data_morning}")
        logger.info(f"FreeBusy afternoon response: {data_afternoon}")
        
        # Check for errors
        if "error" in data_morning:
            return f"Calendar error: {data_morning['error'].get('message', 'Unknown error')}"
        
        if "calendars" not in data_morning:
            return f"Unexpected response from calendar API: {data_morning}"
        
        available_slots = []
        begin = start_10
        end = end_1230
        
        calendar_data = data_morning["calendars"].get(CALENDAR, {})
        morning_busy = calendar_data.get("busy", [])
        
        # If no busy slots, entire morning is available
        if not morning_busy:
            available_slots.append((start_10.strftime("%H:%M"), end_1230.strftime("%H:%M")))
        else:
            for i in range(len(morning_busy)):
                busy_start = datetime.fromisoformat(morning_busy[i]["start"].replace("Z", "+00:00"))
                busy_end = datetime.fromisoformat(morning_busy[i]["end"].replace("Z", "+00:00"))
                if begin < busy_start:
                    available_slots.append((begin.strftime("%H:%M"), busy_start.strftime("%H:%M")))
                begin = busy_end
            # Check if there's time left after last busy slot
            if begin < end:
                available_slots.append((begin.strftime("%H:%M"), end.strftime("%H:%M")))
            

        # Afternoon slots
        begin = start_15
        end = end_19
        
        afternoon_data = data_afternoon.get("calendars", {}).get(CALENDAR, {})
        afternoon_busy = afternoon_data.get("busy", [])
        
        # If no busy slots, entire afternoon is available
        if not afternoon_busy:
            available_slots.append((start_15.strftime("%H:%M"), end_19.strftime("%H:%M")))
        else:
            for i in range(len(afternoon_busy)):
                busy_start = datetime.fromisoformat(afternoon_busy[i]["start"].replace("Z", "+00:00"))
                busy_end = datetime.fromisoformat(afternoon_busy[i]["end"].replace("Z", "+00:00"))
                if begin < busy_start:
                    available_slots.append((begin.strftime("%H:%M"), busy_start.strftime("%H:%M")))
                begin = busy_end
            # Check if there's time left after last busy slot
            if begin < end:
                available_slots.append((begin.strftime("%H:%M"), end.strftime("%H:%M")))
            
        result = "Available time slots for visits: (make up a 30 minute interval from the list of available times) " + str(available_slots)
        logger.info(f"✅ TOOL RESULT: check_available_slots | {result}")
        return result

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
        stt=deepgram.STT(model="nova-3", language="it-IT"),
        #llm=openai.LLM(
        #   model="x-ai/grok-4-fast",
        #    base_url="https://openrouter.ai/api/v1",
        #    api_key=os.getenv("OPENROUTER_API_KEY"),
        #)
        llm=openai.LLM(
            model="kimi-k2-0905-preview",
            base_url="https://api.moonshot.ai/v1",
            api_key=os.getenv("MOONSHOT_API_KEY"),
        )
        ,
        tts=lk_google.TTS(
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
    cli.run_app(server)
