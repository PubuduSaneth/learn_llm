import httpx

# 1. Save the original Client classes
_original_client = httpx.Client
_original_async_client = httpx.AsyncClient

# 2. Define a "force-unverified" version of the Client
class UnverifiedClient(_original_client):
    def __init__(self, *args, **kwargs):
        kwargs['verify'] = False  # Force verify to False
        super().__init__(*args, **kwargs)

# 3. Define a "force-unverified" version of the AsyncClient
class UnverifiedAsyncClient(_original_async_client):
    def __init__(self, *args, **kwargs):
        kwargs['verify'] = False  # Force verify to False
        super().__init__(*args, **kwargs)

# 4. Swap the global httpx classes with our unverified versions
httpx.Client = UnverifiedClient
httpx.AsyncClient = UnverifiedAsyncClient

import os
import google.auth
from pathlib import Path
from google.genai import types
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.apps.app import App, EventsCompactionConfig
from google.adk.agents.context_cache_config import ContextCacheConfig
from google.adk.models import Gemini
from goodmem_adk import GoodmemPlugin

load_dotenv(dotenv_path=Path(__file__).with_name(".env"))

# 1. Define the Models
# FIX #1: Corrected model name from "gemini-3-flash-preview" (doesn't exist)
# to "gemini-3-flash-preview".

main_model = "gemini-3-flash-preview"
summarization_llm = Gemini(model="gemini-1.5-flash")

_, project_id = google.auth.default()
os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

# 2. Define the Policy Specialist Agent
POLICY_MANUAL = """URL to the policy is https://artificialintelligenceact.eu/high-level-summary/ """


# 3. Configure Persistent Memory (The 'Goodmem' Plugin)
# This is where the local database lives
PERSIST_PATH = os.path.join(os.getcwd(), "agent_memory")

persistent_memory = GoodmemPlugin(
    base_url=os.getenv("GOODMEM_BASE_URL"),
    api_key=os.getenv("GOODMEM_API_KEY"),
    embedder_id=os.getenv("GOODMEM_EMBEDDER_ID"),
    space_id=os.getenv("GOODMEM_SPACE_ID"),
    space_name=os.getenv("GOODMEM_SPACE_NAME"),
    debug=os.getenv("GOODMEM_DEBUG", "false").lower() in ("1", "true", "yes", "on"),
    top_k=5,  # Retrieve the 5 most relevant past interactions
)

my_agent = Agent(
    name="compliance_specialist",
    model=Gemini(
        model=main_model,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    static_instruction=f"You are a compliance expert. Use this manual: {POLICY_MANUAL}",
    instruction=(
        "You have access to the user's past interaction history via persistent memory. "
        "Use this history to provide personalized compliance advice. "
        "If they previously mentioned a specific department or role, tailor your citations to them."
        )
)

app = App(
    name='policy_compliance_memory',
    root_agent=my_agent,

    # Attach Persistent Memory
    plugins=[persistent_memory],

    context_cache_config=ContextCacheConfig(
        min_tokens=2048,
        ttl_seconds=3600,   # Keep manual cached for 1 hour
        cache_intervals=15
    ),

    events_compaction_config=EventsCompactionConfig(
        compaction_interval=20,
        overlap_size=5,
    )
)
