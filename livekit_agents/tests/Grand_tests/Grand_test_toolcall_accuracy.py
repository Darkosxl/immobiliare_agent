import pytest
import asyncio
import os
import sys
import logging
from unittest.mock import patch, MagicMock
from rich.console import Console
from rich.table import Table
from rich import box
from dotenv import load_dotenv

# Add parent directory to path to allow imports from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from livekit.agents import AgentSession, inference
from livekit.agents.voice.run_result import FunctionCallEvent
from livekit.plugins import openai, groq, anthropic, google
from agents.it_inbound_agent import RealEstateItalianAgent

load_dotenv()
console = Console()
logger = logging.getLogger("grand-test")

# --- Helpers ---

def get_models():
    """Read LLMs.txt and return list of model strings."""
    path = os.path.join(os.path.dirname(__file__), "LLMs.txt")
    models = []
    if os.path.exists(path):
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    models.append(line)
    return models

def create_llm_instance(model_name: str):
    """Factory to create LLM instance based on prefix."""
    if model_name.startswith("xAI/"):
        return openai.LLM.with_x_ai(model=model_name.replace("xAI/", ""))
    elif model_name.startswith("Groqcloud/") or model_name.startswith("groqcloud/"):
        return groq.LLM(model=model_name.replace("Groqcloud/", "").replace("groqcloud/", ""))
    elif model_name.startswith("openai/"):
        return openai.LLM(model=model_name.replace("openai/", ""))
    elif model_name.startswith("anthropic/"):
        return anthropic.LLM(model=model_name.replace("anthropic/", ""))
    elif model_name.startswith("google/"):
        return google.LLM(model=model_name.replace("google/", ""))
    else:
        # Fallback or local
        return inference.LLM(model=model_name)

class TestableAgent(RealEstateItalianAgent):
    """Test-safe version of the agent that skips on_enter logic like whitelisting."""
    async def on_enter(self, *args, **kwargs):
        pass

# --- Test ---

@pytest.mark.asyncio
async def test_grand_tool_accuracy_benchmark():
    models = get_models()
    if not models:
        console.print("[red]No models found in LLMs.txt[/red]")
        return

    results = []

    console.print(f"[bold cyan]Starting Tool Accuracy Benchmark on {len(models)} models...[/bold cyan]")

    # We mock the tool to avoid real DB calls and to easily track execution
    # We patch the function where it is DEFINED (tools.real_estate_tools)
    with patch("tools.real_estate_tools.get_apartment_info") as mock_get_info:
        # Setup mock behavior
        mock_get_info.return_value = "Abbiamo un bellissimo appartamento in centro a Milano, 90mq, 1200 euro."

        for i, model_name in enumerate(models):
            console.print(f"[{i+1}/{len(models)}] Testing: [yellow]{model_name}[/yellow]...")

            error_details = None
            tool_called = False
            tool_failed = False # captured if the tool function itself raised exc (not applicable with mock usually, unless we check args)

            try:
                llm = create_llm_instance(model_name)

                # Create session with minimal deps (no STT/TTS needed for text run usually, but provided for safety)
                # Note: TestableAgent doesn't need context usually if on_enter is skipped
                agent = TestableAgent()

                async with AgentSession(llm=llm) as session:
                    # Start the agent (binds tools etc)
                    await session.start(agent)

                    # Reset mock for this turn
                    mock_get_info.reset_mock()

                    # SIMULATE USER INPUT
                    # "I'm looking for an apartment in Milan" -> Should trigger get_apartment_info
                    response = await session.run(user_input="Ciao, sto cercando un appartamento in affitto a Milano.")

                    # ANALYZE RESULTS
                    # 1. Did it try to call the tool?
                    # Check events for FunctionCallEvent
                    fnc_events = [e for e in response.events if isinstance(e, FunctionCallEvent)]

                    if fnc_events:
                        # Check if specific tool was called
                        tool_names = [e.item.name for e in fnc_events]
                        if "get_apartment_info" in tool_names:
                            tool_called = True
                        else:
                            error_details = f"Wrong tool: {tool_names}"
                    else:
                        error_details = "No tool called"

                    # 2. Did the mock get called? (Double verification)
                    # If LLM malformed the arguments, the framework might catch it before calling the python function
                    # or pass invalid args.
                    if tool_called:
                        if not mock_get_info.called:
                            # This means the framework received the call but failed to invoke our function
                            # (likely argument validation error)
                            tool_failed = True
                            error_details = "Arg validation failed (Mock not reached)"
                        else:
                            # It reached the function.
                            # Since we mocked it to return string, it "succeeded" in python execution.
                            pass

            except Exception as e:
                error_details = f"Exception: {str(e)}"
                tool_failed = True # System failure

            # Record status
            status = "SUCCESS" if (tool_called and not tool_failed) else "FAIL"
            if not tool_called: status = "MISSING"

            results.append({
                "model": model_name,
                "status": status,
                "tool_called": tool_called,
                "tool_failed": tool_failed,
                "details": error_details or ""
            })

    # --- Reporting ---

    table = Table(title="Grand Test: Tool Call Accuracy", box=box.ROUNDED)
    table.add_column("Model", style="cyan")
    table.add_column("Result", style="bold")
    table.add_column("Call Attempted", style="yellow")
    table.add_column("Call Failed", style="red")
    table.add_column("Details", style="white")

    success_count = 0
    fail_tool_exec = 0
    fail_no_call = 0

    for r in results:
        status_color = "green" if r["status"] == "SUCCESS" else "red"
        table.add_row(
            r["model"],
            f"[{status_color}]{r['status']}[/{status_color}]",
            "Yes" if r["tool_called"] else "No",
            "Yes" if r["tool_failed"] else "No",
            r["details"]
        )

        if r["status"] == "SUCCESS": success_count += 1
        if r["tool_failed"]: fail_tool_exec += 1
        if not r["tool_called"]: fail_no_call += 1

    console.print("\n")
    console.print(table)
    console.print(f"\n[bold]Summary:[/bold]")
    console.print(f"Total Models: {len(models)}")
    console.print(f"Success: [green]{success_count}[/green]")
    console.print(f"Failed (No Call): [red]{fail_no_call}[/red]")
    console.print(f"Failed (Arg/Exec Error): [red]{fail_tool_exec}[/red]")
