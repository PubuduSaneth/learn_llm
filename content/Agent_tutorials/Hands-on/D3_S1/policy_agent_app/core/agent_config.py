from google.adk.agents import LlmAgent
from google.adk.models import Gemini

# Static Policy (Script 1)
STATIC_POLICY = """You are a strict compliance assistant. 
Refuse medical advice. Use active voice."""

# Model setup
llm = Gemini(model_name="gemini-3-flash-preview")

# Agent initialization
policy_agent = LlmAgent(
    name="policy_agent",
    model=llm,
    static_instruction=STATIC_POLICY
)