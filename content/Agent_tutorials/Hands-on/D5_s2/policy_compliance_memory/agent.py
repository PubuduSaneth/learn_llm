import os
from google.adk.agents import Agent
from google.adk.apps import App, EventsCompactionConfig
from google.adk.agents.context_cache_config import ContextCacheConfig
from google.adk.apps.llm_event_summarizer import LlmEventSummarizer
from google.adk.models import Gemini
from goodmem_adk import GoodmemPlugin

# This massive string is what we want to cache!
POLICY_MANUAL = """
https://artificialintelligenceact.eu/high-level-summary/
"""

_, project_id = google.auth.default()
os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

# 1. Define the Models
main_model = "gemini-2.5-flash-preview-09-2025"
summarization_llm = Gemini(model="gemini-1.5-flash")

_, project_id = google.auth.default()
os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

# 2. Define the Policy Specialist Agent
# The 'static_instruction' is what gets Cached.
POLICY_MANUAL = "[Imagine 10,000 words of Corporate Policy here...]"

my_agent = Agent(
    name="compliance-specialist",
    model=Gemini(
        model="gemini-3-flash-preview",   # swap for gemini-3-flash-preview when GA
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    static_instruction=f"You are a compliance expert. Use this manual: {POLICY_MANUAL}",
    instruction=(
        "You have access to the user's past interaction history via persistent memory. "
        "Use this history to provide personalized compliance advice. "
        "If they previously mentioned a specific department or role, tailor your citations to them."
    )
)

# 3. Configure Persistent Memory (The 'Goodmem' Plugin)
# This handles the Silent Observer and Context Injection patterns.
persistent_memory = GoodmemPlugin(
    base_url=os.getenv("GOODMEM_BASE_URL"),
    api_key=os.getenv("GOODMEM_API_KEY"),
    top_k=5 # Retrieve the 5 most relevant past interactions
)

# 4. Initialize the App with the "Triple-Threat" Context Strategy
app = App(
    name='compliance-advisor',
    root_agent=my_agent,
    
    # Attach Persistent Memory
    plugins=[persistent_memory],

    # 1. Cache the massive Policy Manual
    context_cache_config=ContextCacheConfig(
        min_tokens=2048,
        ttl_seconds=3600,   # Keep manual cached for 1 hour
        cache_intervals=15
    ),

    # 2. Compress the current conversation history (using Flash)
    events_compaction_config=EventsCompactionConfig(
        compaction_interval=3,
        overlap_size=1,
        summarizer=LlmEventSummarizer(llm=summarization_llm)
    )
)

