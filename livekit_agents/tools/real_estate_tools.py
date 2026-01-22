import json
import logging
import random
import requests

from groq import Groq
from geopy.distance import geodesic
from livekit.agents import RunContext, function_tool, get_job_context

from utils import database as db
from prompts.it_inbound_prompt import immobiliare_agenzia

logger = logging.getLogger("real-estate-tools")


@function_tool
async def get_apartment_info(
    context: RunContext,
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
            - property_type: "living", "commercial" or "parking"
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
    listing_type = params.get("listing_type", "rent")
    property_type = params.get("property_type", "living")

    # Step 2: Check if we have listings of the requested type (rent vs sale)
    available_listings = db.getCurrentListings(
        Real_Estate_Agency=immobiliare_agenzia,
        property_type=property_type,
        listing_type=listing_type
    )

    if available_listings == "No listings found.":
        # Check what we DO have
        opposite_type = "sale" if listing_type == "rent" else "rent"
        opposite_listings = db.getCurrentListings(
            Real_Estate_Agency=immobiliare_agenzia,
            property_type=property_type,
            listing_type=opposite_type
        )

        if opposite_listings != "No listings found.":
            if listing_type == "rent":
                return json.dumps({
                    "status": "no_rentals",
                    "message": "Non abbiamo immobili in affitto al momento. Trattiamo solo vendite. Posso mostrarti le nostre proprietà in vendita?"
                })
            else:
                return json.dumps({
                    "status": "no_sales",
                    "message": "Non abbiamo immobili in vendita al momento. Trattiamo solo affitti. Posso mostrarti le nostre proprietà in affitto?"
                })
        else:
            return json.dumps({
                "status": "no_listings",
                "message": "Non abbiamo immobili disponibili al momento."
            })

    # Step 3: If no zone provided, return suggestions based on other filters
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

    listings = db.getAllListingsWithCoords(
        Real_Estate_Agency=immobiliare_agenzia,
        property_type=property_type,
        listing_type=listing_type
    )

    # Calculate distance for each listing
    for listing in listings:
        listing['distance_km'] = geodesic(
            user_coords,
            (listing['latitude'], listing['longitude'])
        ).km

    # Sort by distance and get top 3
    top3 = sorted(listings, key=lambda x: x['distance_km'])[:3]

    # No listings with coordinates found for this filter
    if not top3:
        tipo = "in affitto" if listing_type == "rent" else "in vendita"
        return json.dumps({
            "status": "no_nearby",
            "message": f"Non ho trovato immobili {tipo} in zona {zone}. Vuole che cerchi in un'altra zona?"
        })

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


@function_tool
async def immobiliare_offers(context: RunContext, agency: str):
    """Get available service offers/packages for a real estate agency.
    Use this to present special offers to potential sellers/landlords.

    Args:
        agency (str): The name of the agency (e.g., "primacasa")

    Returns:
        A list of available offers for the agency
    """
    logger.info(f"🎁 TOOL: immobiliare_offers | agency={agency}")

    offers = db.get_offers_by_agency(agency)

    if not offers:
        return f"Nessuna offerta disponibile per {agency}."

    offers_text = "\n".join([f"- {offer}" for offer in offers])
    return f"Offerte disponibili per {agency}:\n{offers_text}"


@function_tool
async def note_info(context: RunContext, note: str):
    """Record any relevant information about the caller or property.
    Use this to note down property details, pain points, preferences, or any other relevant info.

    Args:
        note (str): Natural language notes (property details, pain points, preferences, etc.)

    Returns:
        Confirmation that the note was recorded
    """
    logger.info(f"📝 TOOL: note_info | note={note}")

    # Get phone number from context
    agent = context.session.current_agent
    if getattr(agent, 'is_test', False):
        phone_number = "TEST-000000"
    else:
        job_ctx = get_job_context()
        room_name = job_ctx.room.name if job_ctx.room else ""
        phone_number = "Unknown"
        if room_name.startswith("call-"):
            parts = room_name.split("_")
            if len(parts) >= 2:
                phone_number = parts[1]

    # Save note to database
    success = db.add_customer_note(phone_number, note)

    if success:
        return f"Ho annotato: {note}"
    else:
        logger.error(f"Failed to save note for {phone_number}")
        return f"Ho annotato: {note}"
