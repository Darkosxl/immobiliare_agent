"""
Test 4: Full buyer conversation flow.
Simulates a complete conversation from greeting through apartment search to booking.
"""
import pytest
from tests.utils import any_message_matches


@pytest.mark.asyncio
async def test_buyer_route(session, judge_llm, agent):
    """Test the complete buyer conversation flow."""

    await session.start(agent)

    # Turn 1: User greets back, the agent asks if they own a property or are looking for one
    result = await session.run(user_input="Ciao!")
    result.expect.skip_next()

    result = await session.run(user_input="come stai?")
    await any_message_matches(result, judge_llm, intent="asks if they are looking for a house/property or own a house/property")

    # Turn 2: User says they are looking for a house, assistant asks if it is for rent or buy
    result = await session.run(user_input="sto cercando una casa")
    await any_message_matches(result, judge_llm, intent="asks if they are looking to rent or buy")

    # Turn 3: User says they want to buy, assistant asks about budget and preferred area/zone
    result = await session.run(user_input="Voglio comprare")
    await any_message_matches(result, judge_llm, intent="Asks about budget and preferred area/zone")

    # Turn 4: User provides budget and area - triggers apartment search
    result = await session.run(user_input="Ho un budget di 500000 euro, zona Navigli")
    result.expect.contains_function_call(name="get_apartment_info")
    result.expect.contains_function_call_output()
    await any_message_matches(result, judge_llm, intent="Explains available apartments for sale")

    # Turn 5: User asks for more info
    result = await session.run(user_input="Mi puoi dare più informazioni sul primo?")
    await any_message_matches(result, judge_llm, intent="Provides more details about an apartment")

    # Turn 6: User asks about available times
    result = await session.run(user_input="Quando sarebbe possibile visitarlo?")
    result.expect.contains_function_call(name="check_available_slots")
    result.expect.contains_function_call_output()
    await any_message_matches(result, judge_llm, intent="Tells the user which time slots are available for a visit")

    # Turn 7: User wants to schedule a visit
    result = await session.run(user_input="Va bene, prenotiamo per domani alle 15")
    result.expect.contains_function_call(name="schedule_meeting")
    result.expect.contains_function_call_output()
    await any_message_matches(result, judge_llm, intent="Confirms the visit has been scheduled")

    # Turn 8: User thanks and wants to end
    result = await session.run(user_input="Grazie mille, arrivederci")
    await any_message_matches(result, judge_llm, intent="Thanks the user and says goodbye")
