"""
Test: Full outbound opposizioni conversation flow (Path D).
Simulates a complete outbound call where the person is on the "registro delle opposizioni" (do-not-call list).
Based on TASKS from it_outbound_prompt.py Path D.
This tests the agent's ability to recognize and respect the do-not-call request.
"""
import pytest
from utils.tests_utils import any_message_matches
from livekit.agents.voice.run_result import FunctionCallEvent


@pytest.mark.asyncio
async def test_outbound_opposizioni_route(session, judge_llm, outbound_agent):
    """Test the outbound opposizioni flow - user requests to not be called."""

    await session.start(outbound_agent)

    # Turn 1: Agent greets, user answers
    result1 = await session.run(user_input="Pronto, chi parla?")
    result1.expect.skip_next()

    # Turn 2: Agent introduces, user immediately mentions registro opposizioni
    result2 = await session.run(user_input="Senta, io sono iscritto al registro delle opposizioni, non potete chiamarmi")
    await any_message_matches(result2, judge_llm, intent="Apologizes and wishes them a good day before hanging up (TASK 2 - Hang Up)")

    # Verify end_call was called
    tools = {e.item.name for r in [result1, result2] for e in r.events if isinstance(e, FunctionCallEvent)}
    assert "end_call" in tools


@pytest.mark.asyncio
async def test_outbound_opposizioni_route_delayed(session, judge_llm, outbound_agent):
    """Test the outbound opposizioni flow - user mentions it after some conversation."""

    await session.start(outbound_agent)

    # Turn 1: Agent greets, user answers normally
    result1 = await session.run(user_input="Pronto")
    result1.expect.skip_next()

    # Turn 2: User engages briefly - just skip, we only care about the opposizioni handling
    result2 = await session.run(user_input="Si, dimmi")
    result2.expect.skip_next()

    # Turn 3: User is a bit annoyed, mentions opposizioni
    result3 = await session.run(user_input="Ma scusi eh, io ho chiesto di non essere chiamato. Sono nel registro delle opposizioni, lo sapevate?")
    await any_message_matches(result3, judge_llm, intent="Apologizes for the disturbance and wishes them a good day before hanging up")

    # Verify end_call was called
    tools = {e.item.name for r in [result1, result2, result3] for e in r.events if isinstance(e, FunctionCallEvent)}
    assert "end_call" in tools
