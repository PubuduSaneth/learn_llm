from google.adk.agents import Agent

# This massive string is what we want to cache!
POLICY_MANUAL = """
[Insert 50+ pages of Corporate Policy, Legal Guidelines, and HR Rules here...]
"""

my_agent = Agent(
    name="compliance-specialist",
    model="gemini-2.0-pro", # Or your preferred 2026-era model
    static_instruction=f"You are a compliance expert. Use this manual to answer queries: {POLICY_MANUAL}",
    instruction="Be professional, cite specific sections, and always ask if the user needs further clarification."
)
