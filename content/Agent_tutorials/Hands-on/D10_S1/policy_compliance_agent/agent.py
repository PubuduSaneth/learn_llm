import os
import google.auth
from google.adk.models import Gemini
from google.genai import types
from google.adk.agents import Agent
from google.adk.apps.app import App, EventsCompactionConfig
from google.adk.agents.context_cache_config import ContextCacheConfig

# This massive string is what we want to cache!
POLICY_MANUAL = """
https://artificialintelligenceact.eu/high-level-summary/
"""

_, project_id = google.auth.default()
os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

my_agent = Agent(
    name="compliance_specialist",
    model=Gemini(
        model="gemini-3-flash-preview",   # swap for gemini-3-flash-preview when GA
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    static_instruction=f"You are a compliance expert. Use this link {POLICY_MANUAL} to access the manual when answering queries",
    instruction="Be professional, cite specific sections, and always ask if the user needs further clarification."
)

# Configure the ADK Runtime
app = App(
    name='policy_compliance_agent',
    root_agent=my_agent,
    
    # 1. Context Caching: Handles the 'Static Instruction' (Policy Manual)
    context_cache_config=ContextCacheConfig(
        min_tokens=2048,    # Only trigger cache for large prompts
        ttl_seconds=1800,   # Keep the policy manual in cache for 30 mins
        cache_intervals=10  # Automatically refresh the cache after 10 turns
    ),

    # 2. Context Compression: Handles the 'Live History' (The Conversation)
    events_compaction_config=EventsCompactionConfig(
        compaction_interval=3, # Every 3 user turns, summarize the history
        overlap_size=1         # Keep the most recent turn in full to maintain flow
    )
)