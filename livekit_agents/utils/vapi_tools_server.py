"""
VAPI Tools Server - Handles tool calls from VAPI assistant
Run with: uvicorn utils.vapi_tools_server:app --host 0.0.0.0 --port 8080
"""
import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

load_dotenv()

# Import database functions
from utils.database import get_offers_by_agency, add_customer_note

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

    # VAPI sends tool call in message.toolCalls[0].function.arguments
    args = body.get("message", {}).get("toolCalls", [{}])[0].get("function", {}).get("arguments", {})
    note = args.get("note", "")

    # Get phone number from VAPI call metadata
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


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
