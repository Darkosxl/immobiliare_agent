"""
Test 2: Agent greeting behavior test.
Verifies that the agent gives an appropriate greeting when a user says hello.

NOTE: This test uses the real LLM and costs API credits.
"""
import pytest


@pytest.mark.asyncio
async def test_assistant_greeting(session, judge_llm, agent):
    """Test that the agent makes a friendly Italian greeting."""
    await session.start(agent)
    
    result = await session.run(user_input="Ciao, buongiorno")
    
    # Judge if the response is a friendly greeting in Italian
    await (
        result.expect.next_event()
        .is_message(role="assistant")
        .judge(
            judge_llm,  # Use Kimi-K2 via Groq for judging
            intent="Makes a friendly greeting in Italian and offers assistance as a real estate agent."
        )
    )
    
    result.expect.no_more_events()
