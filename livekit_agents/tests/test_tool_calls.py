"""
Test 3: Tool calls test (STUB - for user to implement).

This test should verify:
1. LLM can execute tool calls
2. Tool calls return expected results  
3. LLM explains the tool output appropriately

Example template:
    result = await session.run(user_input="Cerco un appartamento in zona Porta Romana")
    
    # Test that the agent calls get_apartment_info
    fnc_call = result.expect.next_event().is_function_call(
        name="get_apartment_info", 
        arguments={"query": "..."}
    )
    
    # Test that the tool returned output
    result.expect.next_event().is_function_call_output(output="...")
    
    # Test that the agent explains the results
    await (
        result.expect.next_event()
        .is_message(role="assistant")
        .judge(llm, intent="Explains the apartment search results to the user")
    )
    
    result.expect.no_more_events()
"""
import pytest


@pytest.mark.asyncio
async def test_tool_calls(session, llm):
    """
    TODO: Implement tool call testing.
    
    Tests to implement:
    1. get_apartment_info - search for apartments
    2. schedule_meeting - book an appointment
    3. check_available_slots - check calendar availability
    """
    # User to implement
    pass
