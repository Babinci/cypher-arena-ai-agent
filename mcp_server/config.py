from dotenv import load_dotenv
from pathlib import Path
import os

# Load .env from one directory above this file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

HTTP_X_AGENT_TOKEN = os.getenv("AI_AGENT_SECRET_KEY")
if not HTTP_X_AGENT_TOKEN:
    raise ValueError("AI_AGENT_SECRET_KEY not found in .env file or environment variables.")

HEADERS = {"X-AGENT-TOKEN": HTTP_X_AGENT_TOKEN}
BASE_URL = "https://backend.cypher-arena.com/words/agent"
