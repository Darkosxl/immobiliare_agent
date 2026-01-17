"""Test utilities."""
from livekit.agents.voice.run_result import RunResult, ChatMessageEvent


async def any_message_matches(result: RunResult, judge_llms: list, intent: str) -> None:
    """Check if ANY assistant message in the turn matches the intent."""
    messages = [e for e in result.events if isinstance(e, ChatMessageEvent) and e.item.role == "assistant"]

    if not messages:
        raise AssertionError("No assistant messages found")
    
    last_error = None
    for msg in messages:
        for judge_name, judge_llm in judge_llms:
            try:
                await result.expect[result.events.index(msg)].is_message().judge(judge_llm, intent=intent + ". Explain also why the intent is not achieved. Explain everything in english")
                print(f"Acting Judge {judge_name}:")
                return  # One passed - done
            except AssertionError as e:
                last_error = f"{judge_name}: {str(e)}"
                break
            except Exception as e:
                print(f"Error in judge tool calling {judge_name}: {str(e)}")
                last_error = e
                continue

    raise AssertionError(last_error)
