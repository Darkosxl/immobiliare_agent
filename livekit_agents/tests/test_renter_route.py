"""
Test 3: Full renter conversation flow.
Simulates a complete conversation from greeting through apartment search to booking.
"""
import pytest


@pytest.mark.asyncio
async def test_renter_route(session, judge_llm, agent):
    """Test the complete renter conversation flow."""
    
    await session.start(agent)
    
    # Turn 1: User says they're looking for a home
    result = await session.run(user_input="Ciao, sto cercando una casa")
    result.expect.next_event().is_message(role="assistant")  # Agent greets and asks buy/rent
    
    # Turn 2: User says they want to rent
    result = await session.run(user_input="Voglio affittare")
    await (
        result.expect.next_event()
        .is_message(role="assistant")
        .judge(judge_llm, intent="Asks about budget and preferred area/zone")
    )
    
    # Turn 3: User provides budget and area - triggers apartment search
    result = await session.run(user_input="Vorrei spendere massimo 1500 al mese, zona Porta Romana")
    result.expect.next_event(type="function_call", name="get_apartment_info")
    result.expect.next_event(type="function_call_output")
    await (
        result.expect.next_event()
        .is_message(role="assistant")
        .judge(judge_llm, intent="Explains available rental apartments")
    )
    
    # Turn 4: User asks for more info
    result = await session.run(user_input="Mi puoi dare più informazioni sul primo?")
    await (
        result.expect.next_event()
        .is_message(role="assistant")
        .judge(judge_llm, intent="Provides more details about an apartment")
    )
    
    # Turn 5: User asks about available times
    result = await session.run(user_input="Quando sarebbe possibile visitarlo?")
    result.expect.next_event(type="function_call", name="check_available_slots")
    result.expect.next_event(type="function_call_output")
    await (
        result.expect.next_event()
        .is_message(role="assistant")
        .judge(judge_llm, intent="Tells the user which time slots are available for a visit")
    )
    
    # Turn 6: User wants to schedule a visit
    result = await session.run(user_input="Va bene, prenotiamo per domani alle 15")
    result.expect.next_event(type="function_call", name="schedule_meeting")
    result.expect.next_event(type="function_call_output")
    await (
        result.expect.next_event()
        .is_message(role="assistant")
        .judge(judge_llm, intent="Confirms the visit has been scheduled")
    )
    
    # Turn 6: User thanks and wants to end
    result = await session.run(user_input="Grazie mille, arrivederci")
    await (
        result.expect.next_event()
        .is_message(role="assistant")
        .judge(judge_llm, intent="Thanks the user and says goodbye")
    )
