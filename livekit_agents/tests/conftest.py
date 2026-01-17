"""
Shared pytest fixtures for LiveKit agent tests.
"""
import pytest
import os
import sys

# Add parent directory to path so we can import agent modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from livekit.agents import AgentSession
from livekit.plugins import openai, groq

from agents.it_inbound_agent import RealEstateItalianAgent


class _TestableAgent(RealEstateItalianAgent):
    """
    Test-safe version of RealEstateItalianAgent.
    
    Inherits ALL behavior (prompt, tools, LLM logic) but overrides on_enter
    to skip whitelist check which requires a real LiveKit job context.
    """
    async def on_enter(self):
        # Skip whitelist check - no job context in tests
        await self.session.generate_reply(allow_interruptions=False)


@pytest.fixture
def agent():
    """Create a _TestableAgent instance (same as production but test-safe)."""
    return _TestableAgent()


@pytest.fixture
async def llm():
    """Agent LLM - same as production (Grok-4 via xAI)."""
    async with openai.LLM.with_x_ai(model="grok-4-1-fast-non-reasoning") as llm:
        yield llm


@pytest.fixture
async def judge_llm():
    """Judge LLM - Kimi-K2 via Groq (cheaper for evaluating responses)."""
    async with groq.LLM(model="moonshotai/kimi-k2-instruct-0905") as llm:
        yield llm


@pytest.fixture
async def session(llm):
    """Create an AgentSession with the production LLM."""
    async with AgentSession(llm=llm) as session:
        yield session
