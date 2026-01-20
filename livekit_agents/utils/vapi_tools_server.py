"""
VAPI Tools Server - Handles tool calls from VAPI assistant
Run with: uvicorn utils.vapi_tools_server:app --host 0.0.0.0 --port 8069
"""
import os
import requests
from datetime import datetime, timedelta, timezone as tz
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

load_dotenv()

# Import database functions
from utils.database import get_offers_by_agency, add_customer_note
from utils.agents_utils import get_google_token

CALENDAR = os.getenv("CALENDAR_ID")

app = FastAPI()


@app.post("/immobiliare_offers")
async def immobiliare_offers(request: Request):
    """Get available offers for an agency"""
    body = await request.json()

    # VAPI sends tool call in message.toolCalls[0].function.arguments
    args = body.get("message", {}).get("toolCalls", [{}])[0].get("function", {}).get("arguments", {})
    agency = args.get("agency", "primacasa")

    offers = get_offers_by_agency(agency)

    if not offers:
        result = f"Nessuna offerta disponibile per {agency}."
    else:
        result = f"Offerte disponibili per {agency}:\n" + "\n".join([f"- {offer}" for offer in offers])

    return JSONResponse({
        "results": [{"result": result}]
    })


@app.post("/note_info")
async def note_info(request: Request):
    """Record customer notes"""
    body = await request.json()

    args = body.get("message", {}).get("toolCalls", [{}])[0].get("function", {}).get("arguments", {})
    note = args.get("note", "")

    call = body.get("message", {}).get("call", {})
    phone_number = call.get("customer", {}).get("number", "VAPI-UNKNOWN")

    success = add_customer_note(phone_number, note)

    if success:
        result = "Nota registrata."
    else:
        result = "Errore nel salvare la nota."

    return JSONResponse({
        "results": [{"result": result}]
    })


@app.post("/check_available_slots")
async def check_available_slots(request: Request):
    """Check available calendar slots"""
    body = await request.json()
    args = body.get("message", {}).get("toolCalls", [{}])[0].get("function", {}).get("arguments", {})
    date = args.get("date")

    if not date:
        return JSONResponse({"results": [{"result": "Errore: Data mancante"}]})

    try:
        base_date = datetime.fromisoformat(date).replace(tzinfo=tz(timedelta(hours=1)))
        start_10 = base_date.replace(hour=10, minute=0, second=0, microsecond=0)
        end_1230 = base_date.replace(hour=12, minute=30, second=0, microsecond=0)
        start_15 = base_date.replace(hour=15, minute=0, second=0, microsecond=0)
        end_19 = base_date.replace(hour=19, minute=0, second=0, microsecond=0)

        token = get_google_token()
        url = "https://www.googleapis.com/calendar/v3/freeBusy"

        # Morning check
        body_req = {
            "timeMin": start_10.isoformat(),
            "timeMax": end_1230.isoformat(),
            "timeZone": "Europe/Rome",
            "items": [{"id": CALENDAR}]
        }
        response_morning = requests.post(url, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, json=body_req)

        # Afternoon check
        body_req["timeMin"] = start_15.isoformat()
        body_req["timeMax"] = end_19.isoformat()
        response_afternoon = requests.post(url, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, json=body_req)

        data_morning = response_morning.json()
        data_afternoon = response_afternoon.json()

        if "error" in data_morning:
             return JSONResponse({"results": [{"result": f"Calendar error: {data_morning['error'].get('message', 'Unknown error')}"}]})

        available_slots = []

        # Process Morning
        calendar_data = data_morning["calendars"].get(CALENDAR, {})
        morning_busy = calendar_data.get("busy", [])
        begin = start_10
        end = end_1230

        if not morning_busy:
            available_slots.append((start_10.strftime("%H:%M"), end_1230.strftime("%H:%M")))
        else:
            for i in range(len(morning_busy)):
                busy_start = datetime.fromisoformat(morning_busy[i]["start"].replace("Z", "+00:00"))
                busy_end = datetime.fromisoformat(morning_busy[i]["end"].replace("Z", "+00:00"))
                if begin < busy_start:
                    available_slots.append((begin.strftime("%H:%M"), busy_start.strftime("%H:%M")))
                begin = busy_end
            if begin < end:
                available_slots.append((begin.strftime("%H:%M"), end.strftime("%H:%M")))

        # Process Afternoon
        calendar_data = data_afternoon["calendars"].get(CALENDAR, {})
        afternoon_busy = calendar_data.get("busy", [])
        begin = start_15
        end = end_19

        if not afternoon_busy:
            available_slots.append((start_15.strftime("%H:%M"), end_19.strftime("%H:%M")))
        else:
            for i in range(len(afternoon_busy)):
                busy_start = datetime.fromisoformat(afternoon_busy[i]["start"].replace("Z", "+00:00"))
                busy_end = datetime.fromisoformat(afternoon_busy[i]["end"].replace("Z", "+00:00"))
                if begin < busy_start:
                    available_slots.append((begin.strftime("%H:%M"), busy_start.strftime("%H:%M")))
                begin = busy_end
            if begin < end:
                available_slots.append((begin.strftime("%H:%M"), end.strftime("%H:%M")))

        # Expand ranges to 30-min slots
        times = []
        for start_t, end_t in available_slots:
            mins = int(start_t[:2]) * 60 + int(start_t[3:])
            end_mins = int(end_t[:2]) * 60 + int(end_t[3:])
            while mins < end_mins:
                times.append(f"{mins // 60:02d}:{mins % 60:02d}")
                mins += 30

        result = "Available times: " + ", ".join(times)
        return JSONResponse({"results": [{"result": result}]})

    except Exception as e:
        return JSONResponse({"results": [{"result": f"Errore interno: {str(e)}"}]})


@app.post("/schedule_meeting")
async def schedule_meeting(request: Request):
    """Schedule a meeting"""
    body = await request.json()
    args = body.get("message", {}).get("toolCalls", [{}])[0].get("function", {}).get("arguments", {})

    apartment_address = args.get("apartment_address", "Unknown Address")
    date = args.get("date")

    # Get phone number
    call = body.get("message", {}).get("call", {})
    phone_number = call.get("customer", {}).get("number", "Unknown")

    if not date:
        return JSONResponse({"results": [{"result": "Errore: Data mancante"}]})

    try:
        token = get_google_token()
        start = datetime.fromisoformat(date)
        end = start + timedelta(minutes=30)

        url = f"https://www.googleapis.com/calendar/v3/calendars/{CALENDAR}/events"
        body_req = {
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

        response = requests.post(url, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, json=body_req)

        if response.status_code != 200:
             return JSONResponse({"results": [{"result": f"Errore API Calendar: {response.text}"}]})

        result = f"Appuntamento confermato per {apartment_address}"
        return JSONResponse({"results": [{"result": result}]})

    except Exception as e:
        return JSONResponse({"results": [{"result": f"Errore interno: {str(e)}"}]})


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8069)
