"""
Test 3: Full seller conversation flow.
Simulates a complete conversation from greeting through apartment search to booking.
"""
import pytest
from tests.utils import any_message_matches


@pytest.mark.asyncio
async def test_seller_route(session, judge_llm, agent):
    """Test the complete seller conversation flow."""

    await session.start(agent)

    # Turn 1: User greets back, the agent asks if they own a property or are looking for one
    result = await session.run(user_input="Ciao!")
    result.expect.skip_next()

    result = await session.run(user_input="come stai?")
    await any_message_matches(result, judge_llm, intent="asks if they are looking for a house/property or own a house/property")

    # Turn 2: User says they are looking for a house assistant asks if it is for rent or buy
    result = await session.run(user_input="Sono un proprietario")
    await any_message_matches(result, judge_llm, intent="asks for information regarding the property, could be area, how many rooms etc.")

    # Turn 3: User says they are looking to rent, assistant asks about budget and preferred area/zone
    result = await session.run(user_input="È un bilocale di 60 mq in zona Navigli, completamente ristrutturato, molto luminoso e già arredato.")
    await any_message_matches(result, judge_llm, intent="informs the user that they wrote down the details. Then the agent asks if they'd like to book a meeting or be called on the phone as soon as possible")

    # Turn 4: User asks about available times
    result = await session.run(user_input="Quando sarebbe possibile visitarlo?")
    result.expect.contains_function_call(name="check_available_slots")
    result.expect.contains_function_call_output()
    await any_message_matches(result, judge_llm, intent="Tells the user which time slots are available for a visit")

    # Turn 5: User wants to schedule a visit
    result = await session.run(user_input="Va bene, prenotiamo per lunedi alle 15")
    result.expect.contains_function_call(name="schedule_meeting")
    result.expect.contains_function_call_output()
    await any_message_matches(result, judge_llm, intent="Confirms the visit has been scheduled")

    # Turn 6: User thanks and wants to end
    result = await session.run(user_input="Grazie mille, arrivederci")
    await any_message_matches(result, judge_llm, intent="Thanks the user and says goodbye")
