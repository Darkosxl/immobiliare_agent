import pytest
import os
import csv
import asyncio
import statistics
from collections import defaultdict
from rich.console import Console
from rich.table import Table
from rich import box
from livekit.agents import Agent, AgentSession
from livekit.plugins import openai, groq, anthropic, google
from dotenv import load_dotenv
from prompts.it_inbound_prompt import SYSTEM_PROMPT

load_dotenv()


def get_models():
    models_file = os.path.join(os.path.dirname(__file__), "LLMs.txt")
    with open(models_file, "r") as f:
        return [line.strip() for line in f if line.strip()]


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
    elif model_name.startswith("google/"):
        real_name = model_name.replace("google/", "")
        return google.LLM(
            model=real_name,
            vertexai=True
        )
    else:
        # Default to OpenRouter for everything else (Google, OpenAI, Anthropic via OpenRouter)
        return openai.LLM(
            model=model_name,
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )


@pytest.fixture(scope="session", autouse=True)
def init_csv():
    # Results file (Averages)
    results_file = os.path.join(os.path.dirname(__file__), "benchmark_results.csv")
    if not os.path.exists(results_file):
        with open(results_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Model", "Avg TTFT", "Avg TPS", "Avg Duration", "Avg Tokens"])

    # Runs file (Individual)
    runs_file = os.path.join(os.path.dirname(__file__), "benchmark_runs.csv")
    if not os.path.exists(runs_file):
        with open(runs_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Model", "Run", "TTFT", "TPS", "Duration", "Total Tokens"])

@pytest.fixture(scope="session", autouse=True)
def print_summary():
    yield
    console = Console()

    runs_file = os.path.join(os.path.dirname(__file__), "benchmark_runs.csv")

    # Build leaderboard from individual runs
    if os.path.exists(runs_file):
        model_ttfts = defaultdict(list)

        with open(runs_file, "r") as f:
            reader = csv.reader(f)
            next(reader, None)  # Skip header
            for row in reader:
                if len(row) >= 3:
                    model_name = row[0]
                    try:
                        ttft = float(row[2])
                        if ttft > 0:
                            model_ttfts[model_name].append(ttft)
                    except ValueError:
                        pass

        # Calculate avg and variance, sort by avg TTFT (lower is better)
        leaderboard = []
        for model, ttfts in model_ttfts.items():
            if ttfts:
                avg = statistics.mean(ttfts)
                var = statistics.variance(ttfts) if len(ttfts) > 1 else 0.0
                leaderboard.append((model, avg, var, len(ttfts)))

        leaderboard.sort(key=lambda x: x[1])  # Sort by avg TTFT ascending

        table = Table(title="🏆 TTFT Leaderboard (Lower is Better)", box=box.ROUNDED)
        table.add_column("Rank", style="bold yellow", justify="center")
        table.add_column("Model", style="cyan", justify="left")
        table.add_column("Avg TTFT (s)", style="green", justify="right")
        table.add_column("Variance", style="magenta", justify="right")
        table.add_column("Runs", style="dim", justify="center")

        for rank, (model, avg, var, runs) in enumerate(leaderboard, 1):
            table.add_row(
                str(rank),
                model,
                f"{avg:.4f}",
                f"{var:.6f}",
                str(runs)
            )

        console.print(table)

@pytest.mark.asyncio
@pytest.mark.parametrize("model_name", get_models())
async def test_llm_speed(model_name):
    
    llm = create_llm_instance(model_name)

   
    current_metrics = {}
    def on_metrics(m):
        current_metrics['ttft'] = m.ttft
        current_metrics['tps'] = m.tokens_per_second
        current_metrics['duration'] = m.duration
        current_metrics['total_tokens'] = m.total_tokens

    llm.on("metrics_collected", on_metrics)

    
    runs_file = os.path.join(os.path.dirname(__file__), "benchmark_runs.csv")
    results_file = os.path.join(os.path.dirname(__file__), "benchmark_results.csv")

    total_ttft = 0.0
    total_tps = 0.0
    total_duration = 0.0
    total_tokens = 0.0
    successful_runs = 0

    class BenchmarkAgent(Agent):
        def __init__(self):
            super().__init__(instructions=SYSTEM_PROMPT)

    
    for i in range(1, 6):
        current_metrics = {} # Reset metrics

        try:
            agent = BenchmarkAgent()
            async with AgentSession(llm=llm) as session:
                await session.start(agent)
                await session.run(user_input="Ciao!")

            # Metrics collected via callback
        except Exception as e:
            print(f"Error running session for {model_name} run {i}: {e}")
            current_metrics = {} # Ensure empty if failed

        
        ttft = current_metrics.get('ttft', 0)
        tps = current_metrics.get('tps', 0)
        duration = current_metrics.get('duration', 0)
        tokens = current_metrics.get('total_tokens', 0)

        with open(runs_file, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([model_name, i, ttft, tps, duration, tokens])

        # Accumulate
        if tokens > 0: # Assuming successful run has tokens > 0
            total_ttft += ttft
            total_tps += tps
            total_duration += duration
            total_tokens += tokens
            successful_runs += 1

    
    if successful_runs > 0:
        avg_ttft = total_ttft / successful_runs
        avg_tps = total_tps / successful_runs
        avg_duration = total_duration / successful_runs
        avg_tokens = total_tokens / successful_runs
    else:
        avg_ttft = avg_tps = avg_duration = avg_tokens = 0

    with open(results_file, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            model_name,
            f"{avg_ttft:.4f}",
            f"{avg_tps:.2f}",
            f"{avg_duration:.4f}",
            f"{avg_tokens:.2f}"
        ])
