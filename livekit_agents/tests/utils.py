"""Test utilities."""
from livekit.agents.voice.run_result import RunResult, ChatMessageEvent
import asyncio

async def _try_judge(result, msg, judge_name, judge_llm, intent):
    try:
        await result.expect[result.events.index(msg)].is_message().judge(judge_llm, intent=intent)
        return(True, judge_name, None, None)
    except AssertionError as e:
        return (False, judge_name, "assertion", str(e))
    except Exception as e:
        return (False, judge_name, "api", str(e))
    
async def any_message_matches(result: RunResult, judge_llms: list, intent: str) -> None:
    """Check if ANY assistant message in the turn matches the intent."""
    messages = [e for e in result.events if isinstance(e, ChatMessageEvent) and e.item.role == "assistant"]

    if not messages:
        raise AssertionError("No assistant messages found")
    full_intent = intent + ". Explain also why the intent is not achieved. Explain everything in english"
    
    concurrent_judges = judge_llms[:3]
    fallback_judge = judge_llms[3] if len(judge_llms) > 3 else None
    
    successful_judgment = False
    last_error = None
    
    for msg in messages:
        tasks = [_try_judge(result, msg, name, llm, full_intent) for name, llm in concurrent_judges]
        results = await asyncio.gather(*tasks)
        for success, judge_name, error_type, error_msg in results:
            if success:
                print(f"Acting Judge: {judge_name}")
                return
            elif error_type == "assertion":
                successful_judgment = True
                last_error = f"{judge_name}: {error_msg}"
            else:
                print(f"Judge didn't work: {judge_name}")
                last_error = error_msg
                
        if successful_judgment:
            successful_judgment = False
            continue
            
        if fallback_judge:
            name, llm = fallback_judge
            success, judge_name, error_type, error_msg = await _try_judge(result, msg, name, llm, full_intent)
            if success:
                print(f"Acting Judge: {judge_name}")
                return
            elif error_type == "assertion":
                successful_judgment = True
                last_error = f"{judge_name}: {error_msg}"
            else:
                print(f"Judge didn't work: {judge_name}")
                last_error = error_msg
                
    if not successful_judgment:
        raise AssertionError(f"All judges failed. They suck {last_error}")
    raise AssertionError(last_error)
