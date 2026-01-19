"""
Test: Full outbound indirect sales conversation flow (Path C).
Simulates a complete outbound call where landlord is undecided and skeptical.
Based on TASKS from it_outbound_prompt.py Path C (Indirect Sales).
This tests the agent's ability to handle subtle objections and hesitation.
"""
import pytest
from utils.tests_utils import any_message_matches
from livekit.agents.voice.run_result import FunctionCallEvent


@pytest.mark.asyncio
async def test_outbound_indirect_sales_route(session, judge_llm, outbound_agent):
    """Test the complete outbound indirect sales conversation flow (undecided landlord with subtle objections)."""

    await session.start(outbound_agent)

    # Turn 1: Agent greets, user is a bit cold/suspicious
    result1 = await session.run(user_input="Pronto")
    result1.expect.skip_next()

    # Turn 2: User is curt, barely engaging (TASK 1)
    result2 = await session.run(user_input="Chi e? Ho poco tempo")
    await any_message_matches(result2, judge_llm, intent="Introduces themselves from the real estate agency quickly and asks if they have a property they might want to sell or rent")

    # Turn 3: User is vague, doesn't commit to selling or renting (Path C trigger)
    result3 = await session.run(user_input="Boh guarda, ho ereditato un appartamento da mia nonna qualche mese fa, non so bene cosa farci")
    await any_message_matches(result3, judge_llm, intent="Shows empathy and asks questions to understand their situation better")

    # Turn 4: User reveals subtle pain point - emotional attachment + uncertainty about market
    result4 = await session.run(user_input="E che ci sono affezionato, ci andavo da piccolo. Ma sta li vuoto e costa soldi di condominio ogni mese")
    await any_message_matches(result4, judge_llm, intent="Acknowledges the emotional situation and gently explores options without pushing too hard")

    # Turn 5: User is still hesitant, tests the agent with skepticism
    result5 = await session.run(user_input="Si ma le agenzie prendono un sacco di soldi e poi non fanno niente, ho sentito tante storie")
    await any_message_matches(result5, judge_llm, intent="Addresses the concern about agency fees/value without being defensive and explains what they offer differently")

    # Turn 6: User warms up slightly, asks a real question
    result6 = await session.run(user_input="Ma voi come funzionate esattamente? Cioe se affitto poi chi gestisce i problemi?")
    await any_message_matches(result6, judge_llm, intent="Explains the agency's management services or offers")

    # Turn 7: User is more interested but still cautious
    result7 = await session.run(user_input="Mmh ok. E quanto potrei ricavare secondo voi? E in zona Lambrate, 70 metri, due camere")
    await any_message_matches(result7, judge_llm, intent="Offers to provide an estimate or schedule a visit to assess the property properly")

    # Turn 8: User agrees to meet (TASK 4 - Offer Slots)
    result8 = await session.run(user_input="Va bene dai, possiamo vederci cosi vi faccio vedere l'appartamento")
    await any_message_matches(result8, judge_llm, intent="Offers available time slots for a meeting")

    # Turn 9: User picks a time with a minor complication
    result9 = await session.run(user_input="Giovedi... no aspetta giovedi ho una cosa. Venerdi nel tardo pomeriggio ce la fate?")
    await any_message_matches(result9, judge_llm, intent="Confirms availability for Friday afternoon or offers alternatives")

    # Turn 10: User confirms and says goodbye (TASK 5)
    result10 = await session.run(user_input="Ok venerdi alle 17 e 30 allora. Grazie, a venerdi")
    await any_message_matches(result10, judge_llm, intent="Confirms the appointment and says goodbye")

    # Verify required tools were called at some point
    all_results = [result1, result2, result3, result4, result5, result6, result7, result8, result9, result10]
    tools = {e.item.name for r in all_results for e in r.events if isinstance(e, FunctionCallEvent)}
    assert {"check_available_slots", "end_call", "note_info", "immobiliare_offers"} <= tools
