"""Test utilities."""
from livekit.agents.voice.run_result import RunResult, ChatMessageEvent


async def any_message_matches(result: RunResult, judge_llm, intent: str) -> None:
    """Check if ANY assistant message in the turn matches the intent."""
    messages = [e for e in result.events if isinstance(e, ChatMessageEvent) and e.item.role == "assistant"]

    if not messages:
        raise AssertionError("No assistant messages found")

    for msg in messages:
        try:
            await result.expect[result.events.index(msg)].is_message().judge(judge_llm, intent=intent)
            return  # One passed - done
        except AssertionError:
            continue

    raise AssertionError(f"No message matched intent: '{intent}'")
