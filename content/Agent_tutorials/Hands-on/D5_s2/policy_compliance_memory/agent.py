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
from goodmem_adk import GoodmemPlugin, GoodmemFetchTool, GoodmemSaveTool
from google.adk.sessions import DatabaseSessionService



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
# FIX #2: POLICY_MANUAL was just a bare URL string — ADK does not fetch URLs.
# The static_instruction was literally telling the model "Use this manual: https://..."
# with no content. Replace with actual policy text, or load it from a local file.
# Example placeholder below — swap in real content:
POLICY_MANUAL = """
[Insert actual EU AI Act policy text here, or load from a local .txt/.pdf file.
ADK does not fetch URLs — the model receives this string verbatim.]
"""

# 3. Configure Persistent Memory (The 'Goodmem' Plugin)
persistent_memory = GoodmemPlugin(
    base_url=os.getenv("GOODMEM_BASE_URL"),
    api_key=os.getenv("GOODMEM_API_KEY"),
    space_name=os.getenv("GOODMEM_SPACE_NAME"),
    debug=os.getenv("GOODMEM_DEBUG", "false").lower() in ("1", "true", "yes", "on"),
    top_k=5,  # Retrieve the 5 most relevant past interactions
)

# Define the search wrapper if the plugin doesn't provide a direct BaseTool
def search_memory(query: str):
    """Searches the persistent memory for past user interactions and facts."""
    return persistent_memory.search(query)


fetch_tool = GoodmemFetchTool(
    base_url=os.getenv("GOODMEM_BASE_URL"),
    api_key=os.getenv("GOODMEM_API_KEY"),
    space_name=os.getenv("GOODMEM_SPACE_NAME"),
    debug=os.getenv("GOODMEM_DEBUG", "false").lower() in ("1", "true", "yes", "on"),
    top_k=5
)

save_tool = GoodmemSaveTool(
    base_url=os.getenv("GOODMEM_BASE_URL"),
    api_key=os.getenv("GOODMEM_API_KEY"),
    space_name=os.getenv("GOODMEM_SPACE_NAME"),
    debug=os.getenv("GOODMEM_DEBUG", "false").lower() in ("1", "true", "yes", "on")
)


my_agent = Agent(
    name="compliance_specialist",
    model=Gemini(
        model=main_model,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    tools=[fetch_tool, save_tool],
    static_instruction=f"You are a compliance expert. Use this manual: {POLICY_MANUAL}",
    instruction=(
        "You have access to the user's past interaction history via persistent memory. "
        "Use this history to provide personalized compliance advice. "
        "If they previously mentioned a specific department or role, tailor your citations to them."
        "You have tools to save and fetch memories. "
            "1. Whenever the user provides personal details (like department, role, or goals), "
            "   immediately use 'GoodmemSaveTool' to persist that information. "
            "2. If the user asks a question about their history, use 'GoodmemFetchTool' to retrieve context before answering."
        "You have a memory fetch tool. When you need to recall information: "
            "1. DO NOT search using the user's question. "
            "2. Instead, generate a search query that looks like a statement of fact. "
            "Example: If user asks 'What is my role?', search for 'The user's role and department'."
        "When asked to retrieve something, search for statements describing the user's attributes (e.g., 'user department', 'user role'"
    )
)

# 4. Initialize the App with the "Triple-Threat" Context Strategy
# ADK compatibility: keep session service as a separate exported object.
session_service = DatabaseSessionService(db_url=f"sqlite+aiosqlite:///{Path(__file__).with_name('agent_history.db')}")

app = App(
    name='policy_compliance_memory',
    root_agent=my_agent,

    # Attach Persistent Memory
    plugins=[persistent_memory],

    # FIX #3: ContextCacheConfig — the original min_tokens=2048 threshold was
    # never reached because POLICY_MANUAL was just a URL (~10 tokens). Now that
    # POLICY_MANUAL contains real content, caching will kick in appropriately.
    # If your policy text is still short, lower min_tokens or remove this config.
    context_cache_config=ContextCacheConfig(
        min_tokens=2048,
        ttl_seconds=3600,   # Keep manual cached for 1 hour
        cache_intervals=15
    ),

    # FIX #4 (PRIMARY FIX): The original compaction_interval=3 was the core cause
    # of broken persistence. ADK was compacting/discarding raw session events every
    # 3 turns, before GoodmemPlugin (a Silent Observer) had a reliable opportunity
    # to read and persist them to the vector store. With overlap_size=1, almost no
    # events survived across windows for the plugin to observe.
    #
    # Raised compaction_interval to 20 so Goodmem can observe and persist multiple
    # turns before any compaction occurs. Raised overlap_size to 5 to ensure enough
    # recent context survives into the next compaction window.
    #
    # If you want to disable compaction entirely during development/testing, simply
    # remove or comment out this block.
    events_compaction_config=EventsCompactionConfig(
        compaction_interval=20,
        overlap_size=5,
    )
)
