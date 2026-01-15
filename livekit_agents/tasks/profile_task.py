from livekit.agents import AgentTask, function_tool
from livekit.agents.beta.workflows import TaskGroup
from dataclasses import dataclass
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from prompts.it_inbound_prompt import BASE_IDENTITY
#WHITELIST NUMBERS TASK, SPECIFICALLY FOR TESTING (ONE MUST ALSO ADD A PROBER SPAM CALL CHECK AS A TASK)

@dataclass
class ClientProfile:
    phone_number: str #the phone number of the client
    budget: str #the budget of the client (if renter/buyer)
    role: str #the role of the client (buyer, tenant, landlord)
    area: str #which area they are looking to buy/rent, or landlord


class ClientRoleTask(AgentTask[ClientProfile]):
    def __init__(self, chat_ctx=None):
        super().__init__(
            instructions= BASE_IDENTITY + """TASK: Determine if the caller is a landlord, a tenant (someone looking to rent) 
            or a potential buyer. Be polite, talk simple and professional.""",
            chat_ctx=chat_ctx,    
        )
        self._profile = {}

    async def on_enter(self) -> None:
        await self.session.generate_reply(
            instructions="""
            Briefly introduce yourself, then ask the other person if they are looking to buy a house, rent a house or if they are a landlord. 
            """
        )
    @function_tool
    async def landlord(self) -> None:
        """Use this if the client is a landlord"""
        self._profile["role"] = "landlord"
    @function_tool
    async def tenant(self) -> None:
        """Use this if the client is a tenant"""
        self._profile["role"] = "tenant"
    @function_tool
    async def buyer(self) -> None:
        """Use this if the client is a buyer"""
        self._profile["role"] = "buyer"
    
   



    def _check_done()
