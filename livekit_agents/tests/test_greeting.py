"""
Test 2: Agent greeting behavior test.
Verifies that the agent gives an appropriate greeting when a user says hello.

NOTE: This test uses the real LLM and costs API credits.
"""
import pytest

from agents.it_inbound_agent import RealEstateItalianAgent


@pytest.mark.asyncio
async def test_assistant_greeting(session, llm):
    """Test that the agent makes a friendly Italian greeting."""
    agent = RealEstateItalianAgent()
    
    await session.start(agent)
    
    result = await session.run(user_input="Ciao, buongiorno")
    
    # Judge if the response is a friendly greeting in Italian
    await (
        result.expect.next_event()
        .is_message(role="assistant")
        .judge(
            llm, 
            intent="Makes a friendly greeting in Italian and offers assistance as a real estate agent."
        )
    )
    
    result.expect.no_more_events()
