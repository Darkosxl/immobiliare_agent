"""
Test 5: Full seller conversation flow.
Simulates a complete conversation from greeting through property listing to booking.
"""
import pytest
from tests.utils import any_message_matches
from livekit.agents.voice.run_result import FunctionCallEvent


@pytest.mark.asyncio
async def test_seller_route(session, judge_llm, agent):
    """Test the complete seller conversation flow."""

    await session.start(agent)

    # Turn 1: User greets
    result1 = await session.run(user_input="Ciao!")
    result1.expect.skip_next()

    # Turn 2: Agent asks if looking or owning
    result2 = await session.run(user_input="come stai?")
    await any_message_matches(result2, judge_llm, intent="asks if they are looking for a house/property or own a house/property")

    # Turn 3: User says they own, agent asks for property details
    result3 = await session.run(user_input="Sono un proprietario")
    await any_message_matches(result3, judge_llm, intent="asks for information regarding the property, could be area, how many rooms etc.")

    # Turn 4: User provides property details
    result4 = await session.run(user_input="È un bilocale di 60 mq in zona Navigli, completamente ristrutturato, molto luminoso e già arredato.")
    await any_message_matches(result4, judge_llm, intent="informs the user that they wrote down the details. Then the agent asks if they'd like to book a meeting or be called on the phone as soon as possible")

    # Turn 5: User asks about available times
    result5 = await session.run(user_input="Quando sarebbe possibile visitarlo? Va bene sabato?")
    await any_message_matches(result5, judge_llm, intent="Tells the user which time slots are available for a visit")

    # Turn 6: User wants to schedule
    result6 = await session.run(user_input="Va bene, prenotiamo per sabato alle 10:00")
    await any_message_matches(result6, judge_llm, intent="Confirms the visit has been scheduled")

    # Turn 7: User says goodbye
    result7 = await session.run(user_input="Grazie mille, arrivederci")
    await any_message_matches(result7, judge_llm, intent="says goodbye")

    # Verify required tools were called at some point
    tools = {e.item.name for r in [result1, result2, result3, result4, result5, result6, result7] for e in r.events if isinstance(e, FunctionCallEvent)}
    assert {"check_available_slots", "schedule_meeting", "end_call"} <= tools
