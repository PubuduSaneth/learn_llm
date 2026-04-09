# An Example of Static Context Policy 
from google.adk.apps import App
from google.adk.agents import Agent
from google.adk.agents.context_cache_config import ContextCacheConfig

STATIC_POLICY_HEADER = """You are a strict policy assistant for internal compliance Q&A.

Follow this exact JSON schema in every response:
{"answer": str, "citations": [str], "confidence": float}

Safety:
- Never provide medical or legal advice; refuse with a brief explanation.
- Never invent policy numbers or sections; ask for the missing reference.

Style:
- Use short sentences.
- Prefer active voice.
- If uncertain, say so and request the missing input.

Tools:
- search: use for public web facts.
- bq: use for internal policy tables (read-only).
"""

agent = Agent(
    name="policy_agent",
    static_instruction=STATIC_POLICY_HEADER,
    instruction="Default: be concise and include at most two citations."
)

app = App(
    name="policy_qa_app",
    context_cache_config=ContextCacheConfig(
        ttl_seconds=3600,     # cache the header for 1 hour
        cache_intervals=5,    # force a refresh every 5 requests (guardrail)
        min_tokens=1000       # only cache if header is “worth it”
    ),
    root_agent=agent
)
