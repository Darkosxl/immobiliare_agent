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
from livekit.plugins import openai

from agents.it_inbound_agent import RealEstateItalianAgent


@pytest.fixture
def agent():
    """Create a RealEstateItalianAgent instance."""
    return RealEstateItalianAgent()


@pytest.fixture
async def llm():
    """Create the same LLM used in production (Grok-4 via xAI)."""
    async with openai.LLM.with_x_ai(model="grok-4-1-fast-reasoning") as llm:
        yield llm


@pytest.fixture
async def session(llm):
    """Create an AgentSession with the production LLM."""
    async with AgentSession(llm=llm) as session:
        yield session
