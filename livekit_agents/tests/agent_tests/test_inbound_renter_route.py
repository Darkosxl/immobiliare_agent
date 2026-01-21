"""
Test 3: Full renter conversation flow.
Simulates a complete conversation from greeting through apartment search to booking.
"""
import pytest
from utils.tests_utils import any_message_matches
from livekit.agents.voice.run_result import FunctionCallEvent


@pytest.mark.asyncio
async def test_renter_route(session, judge_llm, agent):
    """Test the complete renter conversation flow."""

    await session.start(agent)

    # Turn 1: User greets
    result1 = await session.run(user_input="Ciao!")
    result1.expect.skip_next()

    # Turn 2: Agent asks if looking or owning
    result2 = await session.run(user_input="come stai?")
    await any_message_matches(result2, judge_llm, intent="asks if they are looking for a house/property or own a house/property")

    # Turn 3: User says looking, agent asks rent or buy
    result3 = await session.run(user_input="sto cercando una casa")
    await any_message_matches(result3, judge_llm, intent="asks if they are looking to rent or buy")

    # Turn 4: User says rent, agent asks budget/zone
    result4 = await session.run(user_input="Voglio affittare")
    await any_message_matches(result4, judge_llm, intent="Asks about budget and preferred area/zone")

    # Turn 5: User provides budget/area, agent searches
    result5 = await session.run(user_input="Vorrei spendere massimo 1500 al mese, zona Porta Romana")
    await any_message_matches(result5, judge_llm, intent="Explains available rental apartment(s)")

    # Turn 6: User asks for more info
    result6 = await session.run(user_input="Mi puoi dare più informazioni sul primo?")
    await any_message_matches(result6, judge_llm, intent="Provides more details about an apartment")

    # Turn 7: User asks about available times
    result7 = await session.run(user_input="Quando sarebbe possibile visitarlo? Va bene sabato?")
    await any_message_matches(result7, judge_llm, intent="Tells the user which time slots are available for a visit")

    # Turn 8: User wants to schedule
    result8 = await session.run(user_input="Va bene, prenotiamo per sabato alle 10:00")
    await any_message_matches(result8, judge_llm, intent="Confirms the visit has been scheduled")

    # Turn 9: User says goodbye
    result9 = await session.run(user_input="Grazie mille, arrivederci")
    await any_message_matches(result9, judge_llm, intent="says goodbye")

    # Verify required tools were called at some point
    tools = {e.item.name for r in [result1, result2, result3, result4, result5, result6, result7, result8, result9] for e in r.events if isinstance(e, FunctionCallEvent)}
    assert {"get_apartment_info", "check_available_slots", "schedule_meeting", "end_call"} <= tools
