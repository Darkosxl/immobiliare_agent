from livekit.agents import AgentTask, function_tool


#WHITELIST NUMBERS TASK, SPECIFICALLY FOR TESTING (ONE MUST ALSO ADD A PROBER SPAM CALL CHECK AS A TASK)
class HangUpNonWhitelistedCall(AgentTask[bool]):
    def __init__(self, chat_ctx=None):
        super().__init__(
            instructions="Check from the whitelist if the number calling is an allowed number"
            chat_ctx=chat_ctx,    
        )

    async def on_enter(self) -> None:
        await self.session.generate_reply(
            instructions="""
            Briefly introduce yourself, then get the whitelist of numbers
            and say arrivederci and hang up the call if the current number is not whitelisted
            the tool checkWhiteListed will give you what you need
            """
        )
    @function_tool
    async def checkWhiteListed(self) -> None:
        
    @function_tool
    async def Whitelisted(self) -> None:
        """Use this when the users number is whitelisted"""
        self.complete(True)
    @function_tool
    async def SpamCall(self) -> None:
        """Use this when the other number is NOT whitelisted"""
        self.complete(False)
    