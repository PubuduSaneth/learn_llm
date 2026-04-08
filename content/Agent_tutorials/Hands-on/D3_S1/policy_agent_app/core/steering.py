from dataclasses import dataclass
from typing import Optional, Tuple

@dataclass
class SteeringInputs:
    goal: str
    style: str = "concise"
    confidence_range: Tuple[float, float] = (0.6, 0.9)

def build_turn_instruction(s: SteeringInputs) -> str:
    return (
        f"Goal: {s.goal}\n"
        f"Style: {s.style}\n"
        f"Return confidence between {s.confidence_range[0]} and {s.confidence_range[1]}."
    )