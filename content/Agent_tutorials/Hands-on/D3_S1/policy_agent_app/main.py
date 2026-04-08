from core.steering import SteeringInputs, build_turn_instruction
from core.agent_config import policy_agent

def route_intent(message: str) -> str:
    if "summarize" in message.lower():
        return "Summarize this document briefly."
    return "Answer the user directly."

def chat(user_message: str):
    # 1. Determine the goal
    goal = route_intent(user_message)
    
    # 2. Build the dynamic instruction
    turn_instruction = build_turn_instruction(
        SteeringInputs(goal=goal, style="Professional")
    )
    
    # 3. Inject instruction into agent and run
    policy_agent.instruction = turn_instruction
    return policy_agent.run(user_message=user_message)

if __name__ == "__main__":
    user_in = input("Ask the Policy Agent: ")
    print(chat(user_in))