# agent.py
# Context-Engineering demo: static policy header (cached) + per-turn steering
# Project created with: uv run adk create policy_agent

import dotenv
from google.adk.agents import LlmAgent
from google.adk.models import Gemini
from google.adk.apps import App
from google.genai import types

try:
    from .app_setup import STATIC_POLICY_HEADER, CACHE_CONFIG
    from .steering import SteeringInputs, build_turn_instruction
except ImportError:
    from app_setup import STATIC_POLICY_HEADER, CACHE_CONFIG
    from steering import SteeringInputs, build_turn_instruction

dotenv.load_dotenv()

# ── 1. Static context layer ────────────────────────────────────────────────────
# STATIC_POLICY_HEADER is cached by the App's ContextCacheConfig (1 h TTL,
# refreshed every 5 requests).  It is never regenerated per turn.

# ── 2. Default turn steering ───────────────────────────────────────────────────
# Provides sensible defaults when chat_handler doesn't supply a SteeringInputs.
_default_steering = SteeringInputs(
    goal="Answer the user's compliance question accurately.",
    style="concise",
    max_cites=2,
    confidence_range=(0.6, 0.9),
)

# ── 3. Root agent ──────────────────────────────────────────────────────────────
root_agent = LlmAgent(
    name="policy_agent",
    model=Gemini(
        model="gemini-3-flash-preview",   # swap for gemini-3-flash-preview when GA
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    # static_instruction is the stable, cache-worthy system prompt
    static_instruction=STATIC_POLICY_HEADER,
    # instruction is the *default* per-turn override; chat_handler replaces this
    # dynamically via agent.instruction = build_turn_instruction(steering)
    instruction=build_turn_instruction(_default_steering),
    tools=[],   # add tool toolsets here, e.g. search_toolset, bq_toolset
)

# ── 4. Attach agent to App (picks up ContextCacheConfig from app_setup) ────────

app = App(
    name="policy_agent",
    context_cache_config=CACHE_CONFIG,
    root_agent=root_agent,        # pass LlmAgent directly, no orphan
)
