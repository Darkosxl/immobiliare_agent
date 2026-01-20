"""
Shared pytest fixtures for LiveKit agent tests.
"""
from agents.it_inbound_agent import RealEstateItalianAgent
from agents.it_outbound_agent import RealEstateItalianOutboundAgent

import pytest
import os
import sys
from contextlib import AsyncExitStack


# Add parent directory to path so we can import agent modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from livekit.agents import AgentSession
from livekit.plugins import openai, groq



class _TestableAgent(RealEstateItalianAgent):
    """
    Test-safe version of RealEstateItalianAgent.

    Inherits ALL behavior (prompt, tools, LLM logic) but overrides on_enter
    to skip whitelist check which requires a real LiveKit job context.
    """
    is_test = True

    async def on_enter(self):
        # Skip whitelist check - no job context in tests
        await self.session.generate_reply(allow_interruptions=False)


@pytest.fixture
def agent():
    """Create a _TestableAgent instance (same as production but test-safe)."""
    return _TestableAgent()


class _TestableOutboundAgent(RealEstateItalianOutboundAgent):
    """
    Test-safe version of RealEstateItalianOutboundAgent.

    Inherits ALL behavior (prompt, tools, LLM logic) but overrides on_enter
    to skip SIP call which requires a real LiveKit job context.
    """
    is_test = True

    async def on_enter(self):
        # Skip SIP call - no job context in tests
        await self.session.generate_reply(allow_interruptions=False)


@pytest.fixture
def outbound_agent():
    """Create a _TestableOutboundAgent instance (same as production but test-safe)."""
    return _TestableOutboundAgent()


@pytest.fixture
async def llm():
    """Agent LLM - same as production (Grok-4 via xAI)."""
    async with openai.LLM.with_x_ai(model="grok-4-1-fast-non-reasoning") as llm:
        yield llm


@pytest.fixture
async def judge_llm():
    """Judge LLMs with fallback - multiple providers for reliability."""
    async with AsyncExitStack() as stack:
        judges = [
            ("kimi-k2", await stack.enter_async_context(groq.LLM(model="moonshotai/kimi-k2-instruct-0905"))),
            ("gpt-oss-120b", await stack.enter_async_context(groq.LLM(model="openai/gpt-oss-120b"))),
            ("gemini-3-flash", await stack.enter_async_context(openai.LLM(
                model="google/gemini-3-flash-preview",
                base_url="https://openrouter.ai/api/v1",
                api_key=os.getenv("OPENROUTER_API_KEY"),
            ))),
            ("gpt-5-mini", await stack.enter_async_context(openai.LLM(
                model="openai/gpt-5-mini",
                base_url="https://openrouter.ai/api/v1",
                api_key=os.getenv("OPENROUTER_API_KEY"),
            ))),
        ]
        yield judges


@pytest.fixture
async def session(llm):
    """Create an AgentSession with the production LLM."""
    async with AgentSession(llm=llm) as session:
        yield session
