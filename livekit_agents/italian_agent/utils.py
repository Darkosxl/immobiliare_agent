import os
from dotenv import load_dotenv

load_dotenv()

async def check_whitelisted(self: str) -> bool:
    phone_number = "Unknown"
    if self.startswith("call-"):
        parts = self.split("_")
        if len(parts) >= 2:
            phone_number = parts[1]
    
    whitelist_path = os.getenv("WHITELIST")
    if not whitelist_path:
        return True
    
    
    with open(whitelist_path) as file:
        for line in file:
            if phone_number in line.strip():
                return True
    return False
