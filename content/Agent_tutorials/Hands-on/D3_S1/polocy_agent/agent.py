import dotenv
from google.adk.apps import App
from google.adk.agents import LlmAgent, Context
from google.adk.agents.context_cache_config import ContextCacheConfig
from google.adk.models import Gemini
from google.genai import types
from .steering import SteeringInputs, build_turn_instruction

dotenv.load_dotenv()


# 1. Initialize Gemini 3 Flash
llm = Gemini(
    model="gemini-3-flash-preview",
    retry_options=types.HttpRetryOptions(attempts=3),
)

# 2. Define the Static Policy (Script 1)
STATIC_POLICY = """You are a strict compliance assistant.
Refuse medical advice. Use active voice."""

# 3. Dynamic Steering Callback (Script 3 Logic)
# This function runs every time a user sends a message.
def dynamic_steering_callback(ctx: Context):
    user_msg = ctx.session.last_user_message.text.lower()

    # Simple intent routing
    if "summarize" in user_msg:
        goal = "Summarize the findings."
    elif "compare" in user_msg:
        goal = "Compare the two policies in a table."
    else:
        goal = "Answer the user's question directly."

    # Generate the instruction and update the agent
    new_instr = build_turn_instruction(SteeringInputs(goal=goal, style="Concise"))
    ctx.agent.instruction = new_instr

# 4. Initialize the Agent
root_agent = LlmAgent(
    name="policy_agent",
    model=llm,
    static_instruction=STATIC_POLICY,
    before_agent_callback=dynamic_steering_callback,  # This links your steering logic
)

# 5. Define the App (Script 1)
app = App(
    name="compliance_app",
    root_agent=root_agent,
    context_cache_config=ContextCacheConfig(ttl_seconds=3600, min_tokens=1000),
)
