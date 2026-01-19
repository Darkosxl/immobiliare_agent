"""
Test 2: Agent greeting behavior test.
Verifies that the agent gives an appropriate greeting when a user says hello.

NOTE: This test uses the real LLM and costs API credits.
"""

import pytest
from utils.tests_utils import any_message_matches

@pytest.mark.asyncio
async def test_assistant_greeting(session, judge_llm, agent):
    """Test that the agent makes a friendly Italian greeting."""
    await session.start(agent)
    
    result = await session.run(user_input="Ciao, buongiorno")
    
    await any_message_matches(result, judge_llm, intent="Makes a friendly greeting in Italian and offers assistance as a real estate agent. If it is understandable by a human, that means it works, be a little lenient and think big picture in your evaluation.")
    result.expect.no_more_events()
