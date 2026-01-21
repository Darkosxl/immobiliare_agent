import pytest
import os
import csv
import statistics
from collections import defaultdict
from rich.console import Console
from rich.table import Table
from rich import box
from livekit.agents import Agent, AgentSession, function_tool, RunContext, mock_tools
from livekit.agents.voice.run_result import FunctionCallEvent
from livekit.plugins import openai, groq, anthropic, google
from dotenv import load_dotenv
from prompts.it_inbound_prompt import SYSTEM_PROMPT

load_dotenv()


def get_models():
    models_file = os.path.join(os.path.dirname(__file__), "LLMs.txt")
    with open(models_file, "r") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]


def create_llm_instance(model_name):
    if model_name.startswith("xAI/"):
        real_name = model_name.replace("xAI/", "")
        return openai.LLM.with_x_ai(model=real_name)
    elif model_name.startswith("Groqcloud/") or model_name.startswith("groqcloud/"):
        real_name = model_name.replace("Groqcloud/", "").replace("groqcloud/", "")
        return groq.LLM(model=real_name)
    elif model_name.startswith("anthropic/"):
        real_name = model_name.replace("anthropic/", "")
        return anthropic.LLM(model=real_name)
    elif model_name.startswith("openai/"):
        real_name = model_name.replace("openai/", "")
        return openai.LLM(model=real_name)
    elif model_name.startswith("google/"):
        real_name = model_name.replace("google/", "")
        return google.LLM(model=real_name, vertexai=True)
    else:
        return openai.LLM(
            model=model_name,
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )


# --- Mock Tool ---
@function_tool
async def get_apartment_info(context: RunContext, query: str):
    """Search for apartments based on the caller's requirements.

    Args:
        query: Natural language description of what the caller is looking for.
    """
    return "Abbiamo un bellissimo appartamento in centro a Milano, 90mq, 1200 euro al mese."


class ToolTestAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions=SYSTEM_PROMPT,
            tools=[get_apartment_info]
        )


# Mock function for tracking tool calls
def _mock_get_apartment_info(query: str) -> str:
    return "Abbiamo un bellissimo appartamento in centro a Milano, 90mq, 1200 euro al mese."


# User input with enough detail that the prompt says to call the tool
# Per the prompt: "Whenever a caller requests information, run the relevant tool first"
# This provides zone + budget + intent = should trigger tool call
USER_INPUT = "Buongiorno, cerco un appartamento in affitto zona Porta Romana, budget massimo 1500 euro al mese, due camere."


@pytest.fixture(scope="session", autouse=True)
def init_csv():
    # Results file (Averages)
    results_file = os.path.join(os.path.dirname(__file__), "toolcall_results.csv")
    if not os.path.exists(results_file):
        with open(results_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Model", "Avg TTFT", "Accuracy %", "Success", "Total Runs"])

    # Runs file (Individual)
    runs_file = os.path.join(os.path.dirname(__file__), "toolcall_runs.csv")
    if not os.path.exists(runs_file):
        with open(runs_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Model", "Run", "TTFT", "Tool Called", "Tool Name", "Status"])


@pytest.fixture(scope="session", autouse=True)
def print_summary():
    yield
    console = Console()

    runs_file = os.path.join(os.path.dirname(__file__), "toolcall_runs.csv")

    if os.path.exists(runs_file):
        model_data = defaultdict(lambda: {"ttfts": [], "successes": 0, "total": 0})

        with open(runs_file, "r") as f:
            reader = csv.reader(f)
            next(reader, None)  # Skip header
            for row in reader:
                if len(row) >= 6:
                    model_name = row[0]
                    try:
                        ttft = float(row[2])
                        status = row[5]
                        if ttft > 0:
                            model_data[model_name]["ttfts"].append(ttft)
                        model_data[model_name]["total"] += 1
                        if status == "SUCCESS":
                            model_data[model_name]["successes"] += 1
                    except ValueError:
                        pass

        # Build leaderboard sorted by accuracy (higher is better), then by TTFT (lower is better)
        leaderboard = []
        for model, data in model_data.items():
            if data["ttfts"]:
                avg_ttft = statistics.mean(data["ttfts"])
                ttft_var = statistics.variance(data["ttfts"]) if len(data["ttfts"]) > 1 else 0.0
            else:
                avg_ttft = float('inf')
                ttft_var = 0.0
            accuracy = (data["successes"] / data["total"] * 100) if data["total"] > 0 else 0
            leaderboard.append((model, accuracy, avg_ttft, ttft_var, data["successes"], data["total"]))

        # Sort by accuracy desc, then TTFT asc
        leaderboard.sort(key=lambda x: (-x[1], x[2]))

        table = Table(title="🏆 Tool Call Benchmark Leaderboard", box=box.ROUNDED)
        table.add_column("Rank", style="bold yellow", justify="center")
        table.add_column("Model", style="cyan", justify="left")
        table.add_column("Accuracy", style="green", justify="right")
        table.add_column("Avg TTFT (s)", style="magenta", justify="right")
        table.add_column("TTFT Var", style="dim", justify="right")
        table.add_column("Success/Total", style="white", justify="center")

        for rank, (model, accuracy, avg_ttft, ttft_var, successes, total) in enumerate(leaderboard, 1):
            ttft_str = f"{avg_ttft:.4f}" if avg_ttft != float('inf') else "N/A"
            table.add_row(
                str(rank),
                model,
                f"{accuracy:.1f}%",
                ttft_str,
                f"{ttft_var:.6f}",
                f"{successes}/{total}"
            )

        console.print(table)


@pytest.mark.asyncio
@pytest.mark.parametrize("model_name", get_models())
async def test_toolcall_accuracy(model_name):
    runs_file = os.path.join(os.path.dirname(__file__), "toolcall_runs.csv")
    results_file = os.path.join(os.path.dirname(__file__), "toolcall_results.csv")

    total_ttft = 0.0
    successful_runs = 0
    total_runs = 5

    for i in range(1, total_runs + 1):
        current_metrics = {}
        tool_called = False
        tool_name = ""
        status = "FAIL"

        try:
            llm = create_llm_instance(model_name)

            def on_metrics(m):
                current_metrics['ttft'] = m.ttft
                current_metrics['tps'] = m.tokens_per_second
                current_metrics['duration'] = m.duration
                current_metrics['total_tokens'] = m.total_tokens

            llm.on("metrics_collected", on_metrics)

            async with llm:
                agent = ToolTestAgent()
                async with AgentSession(llm=llm) as session:
                    await session.start(agent)

                    with mock_tools(ToolTestAgent, {"get_apartment_info": _mock_get_apartment_info}):
                        response = await session.run(user_input=USER_INPUT)

                        # Check if tool was called by looking at function call events
                        fnc_events = [e for e in response.events if isinstance(e, FunctionCallEvent)]

                        if fnc_events:
                            tool_names = [e.item.name for e in fnc_events]
                            tool_name = ", ".join(tool_names)
                            if "get_apartment_info" in tool_names:
                                tool_called = True
                                status = "SUCCESS"
                            else:
                                status = "WRONG_TOOL"
                        else:
                            status = "NO_CALL"

        except Exception as e:
            status = "ERROR"
            tool_name = str(e)[:50]

        ttft = current_metrics.get('ttft', 0)

        with open(runs_file, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([model_name, i, ttft, tool_called, tool_name, status])

        if status == "SUCCESS":
            successful_runs += 1
            if ttft > 0:
                total_ttft += ttft

    # Write aggregate results
    avg_ttft = total_ttft / successful_runs if successful_runs > 0 else 0
    accuracy = (successful_runs / total_runs) * 100

    with open(results_file, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            model_name,
            f"{avg_ttft:.4f}",
            f"{accuracy:.1f}",
            successful_runs,
            total_runs
        ])
