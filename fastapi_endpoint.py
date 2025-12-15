

@app.route("/vapi/tool-call", methods=["POST"])
def tool_call():
    data = request.json
    tool_calls = data["message"]["toolCalls"]
    for tool_call in tool_calls:
        tool_name = tool_call["function"]["name"]
        args = tool_call["function"]["arguments"]
        
        if tool_name == "Check_google_calendar_availability":
            calendar_check_availability_tool(args)
        elif tool_name == "Setup_google_calendar_meeting":
            calendar_meeting_create_tool(args)
        elif tool_name == "Lookup_apartment_info":
            lookup_apartment_info_tool(args)

def calendar_check_availability_tool(args):
    return
def calendar_meeting_create_tool(args):
    return
def lookup_apartment_info_tool(args):
    return