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

# """
# app_setup.py instantiates agent and passes it to App(root_agent=agent) at import time.
# That means when agent.py does from app_setup import app, the App is already constructed with the bare Agent as its root.
# We then mutate app.root_agent after the fact.
# This works as long as ADK's App allows post-construction root_agent reassignment
#     — which current ADK does — but if a future ADK version freezes the App after init,
#     it would silently keep the bare Agent.
# The safer long-term pattern is to not construct the App in app_setup.py at all,
#     and instead keep it only as a config/constants module:
# """

# agent = Agent(
#     name="policy_agent",
#     static_instruction=STATIC_POLICY_HEADER,
#     instruction="Default: be concise and include at most two citations."
# )

# app = App(
#     name="policy_qa_app",
#     context_cache_config=ContextCacheConfig(
#         ttl_seconds=3600,     # cache the header for 1 hour
#         cache_intervals=5,    # force a refresh every 5 requests (guardrail)
#         min_tokens=1000       # only cache if header is “worth it”
#     ),
#     root_agent=agent
# )

CACHE_CONFIG = ContextCacheConfig(ttl_seconds=3600, cache_intervals=5, min_tokens=1000)
