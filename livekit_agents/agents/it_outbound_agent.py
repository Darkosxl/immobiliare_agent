
from livekit_agents.agents.it_inbound_agent import RealEstateItalianAgent


logger = logging.getLogger("grok-agent")
logger.setLevel(logging.INFO)
load_dotenv(".env")
CALENDAR = os.getenv("CALENDAR_ID")

class RealEstateItalianOutboundAgent(RealEstateItalianAgent):
    