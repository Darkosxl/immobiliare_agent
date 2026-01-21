"""
Test: Full outbound direct sales conversation flow (Path B).
Simulates a complete outbound call where landlord wants to sell/rent.
Based on TASKS from it_outbound_prompt.py Path B (Direct Sales).
This tests the agent's ability to handle a direct but still challenging conversation.
"""
import pytest
from utils.tests_utils import any_message_matches
from livekit.agents.voice.run_result import FunctionCallEvent


@pytest.mark.asyncio
async def test_outbound_direct_sales_route(session, judge_llm, outbound_agent):
    """Test the complete outbound direct sales conversation flow with realistic challenges."""

    await session.start(outbound_agent)

    # Turn 1: Agent greets (Michele introduces himself), user responds quickly
    result1 = await session.run(user_input="Si pronto")
    result1.expect.skip_next()

    # Turn 2: User is busy, agent needs to be quick (TASK 1)
    result2 = await session.run(user_input="Senta sono al lavoro, chi e e cosa vuole?")
    await any_message_matches(result2, judge_llm, intent="Introduces themselves quickly and gets to the point about helping sell or rent property")

    # Turn 3: User is direct about wanting to sell but skeptical
    result3 = await session.run(user_input="Ah ok. Guarda si, ho un appartamento che voglio vendere da mesi ma le agenzie che ho sentito chiedono troppo")
    await any_message_matches(result3, judge_llm, intent="Shows interest in their situation and asks about the property to understand better (TASK 2 - Qualify the sale)")

    # Turn 4: User provides info but throws in a complaint about previous agencies
    result4 = await session.run(user_input="E un 90 metri zona Isola, ristrutturato. L'altra agenzia voleva il 4 percento, assurdo")
    await any_message_matches(result4, judge_llm, intent="Acknowledges the property details and addresses the pricing concern, mentions their offers")

    # Turn 5: User pushes back on fees
    result5 = await session.run(user_input="Si ma voi quanto prendete? Perche se e uguale non mi interessa")
    await any_message_matches(result5, judge_llm, intent="Explains the agency's fee structure or offers without being defensive")

    # Turn 6: User is somewhat convinced but wants something in return
    result6 = await session.run(user_input="Mmh ok sembra meglio. Ma prima di decidere vorrei una valutazione del prezzo")
    await any_message_matches(result6, judge_llm, intent="Offers to do a property valuation and suggests scheduling a meeting")

    # Turn 7: User agrees to meet but has specific constraints (TASK 4 - Offer Slots)
    result7 = await session.run(user_input="Va bene ma io posso solo dopo le 18, lavoro fino a tardi")
    await any_message_matches(result7, judge_llm, intent="Offers available time slots in the evening or acknowledges the constraint")

    # Turn 8: User picks a time with some back and forth
    result8 = await session.run(user_input="Martedi? No martedi no. Giovedi alle 18 e 30 potrebbe andare")
    await any_message_matches(result8, judge_llm, intent="Confirms the Thursday 18:30 appointment is available and books it")

    # Turn 9: User confirms and ends abruptly (TASK 5)
    result9 = await session.run(user_input="Ok perfetto. Mi devo scappare, ci vediamo giovedi")
    await any_message_matches(result9, judge_llm, intent="Confirms and says goodbye appropriately")

    # Verify required tools were called at some point
    all_results = [result1, result2, result3, result4, result5, result6, result7, result8, result9]
    tools = {e.item.name for r in all_results for e in r.events if isinstance(e, FunctionCallEvent)}
    assert {"check_available_slots", "end_call", "note_info", "immobiliare_offers"} <= tools
