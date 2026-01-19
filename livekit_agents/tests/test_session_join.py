"""
Test: Session join verification for all agents.
Verifies that agents can successfully join a LiveKit session.
"""
import pytest


@pytest.mark.asyncio
async def test_inbound_agent_joins_session(session, agent):
    """Test that the inbound agent can join a session and respond."""
    await session.start(agent)

    # Agent should be able to receive input and produce output
    result = await session.run(user_input="Pronto")

    # Verify we got a response (agent is running)
    assert len(result.events) > 0, "Agent did not produce any events after joining session"


@pytest.mark.asyncio
async def test_outbound_agent_joins_session(session, outbound_agent):
    """Test that the outbound agent can join a session and respond."""
    await session.start(outbound_agent)

    # Agent should be able to receive input and produce output
    result = await session.run(user_input="Pronto")

    # Verify we got a response (agent is running)
    assert len(result.events) > 0, "Agent did not produce any events after joining session"
