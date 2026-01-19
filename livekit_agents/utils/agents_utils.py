import os
import json
import tempfile
import logging

from google.auth.transport.requests import Request
from google.oauth2 import service_account

logger = logging.getLogger("agents-utils")

#write the json to a temp file
_google_creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
if _google_creds.strip().startswith("{"):
    _creds_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
    _creds_file.write(_google_creds)
    _creds_file.close()
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = _creds_file.name
    logger.info(f"Wrote Google credentials to temp file: {_creds_file.name}")

def get_google_token():
    """Get OAuth token from service account credentials.
    
    GOOGLE_APPLICATION_CREDENTIALS can be either:
    - A file path to the JSON file
    - The raw JSON string (for environments where you can't mount files)
    """
    creds_value = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    scopes = ["https://www.googleapis.com/auth/calendar"]
    
    try:
        creds_info = json.loads(creds_value)
        credentials = service_account.Credentials.from_service_account_info(
            creds_info, scopes=scopes
        )
    except (json.JSONDecodeError, TypeError):
        credentials = service_account.Credentials.from_service_account_file(
            creds_value, scopes=scopes
        )
    
    credentials.refresh(Request())
    return credentials.token