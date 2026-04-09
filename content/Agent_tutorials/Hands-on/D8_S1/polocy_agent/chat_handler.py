# chat_handler.py
# Runtime loop: accepts per-turn SteeringInputs, injects them as the agent's
# dynamic instruction, then runs one conversation turn.

from __future__ import annotations

import asyncio
import json
from typing import Optional

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from agent import app, root_agent                          # wired agent + App
from steering import SteeringInputs, build_turn_instruction


# ── Session bootstrap ──────────────────────────────────────────────────────────
_session_service = InMemorySessionService()
_APP_NAME = app.name
_USER_ID  = "default_user"
_SESSION_ID = "default_session"

async def _ensure_session() -> None:
    """Create the ADK session once; no-op on subsequent calls."""
    existing = await _session_service.get_session(
        app_name=_APP_NAME,
        user_id=_USER_ID,
        session_id=_SESSION_ID,
    )
    if existing is None:
        await _session_service.create_session(
            app_name=_APP_NAME,
            user_id=_USER_ID,
            session_id=_SESSION_ID,
            state={},
        )


# ── Core turn function ─────────────────────────────────────────────────────────
async def run_turn(
    user_message: str,
    steering: Optional[SteeringInputs] = None,
) -> dict:
    """
    Run one conversation turn.

    Parameters
    ----------
    user_message : str
        The raw text the user typed.
    steering : SteeringInputs | None
        Per-turn context knobs.  If None, the agent keeps its current
        instruction (set at startup or from the previous turn).

    Returns
    -------
    dict
        Parsed JSON matching the policy schema:
        {"answer": str, "citations": [str], "confidence": float}
        Falls back to {"answer": raw_text, "citations": [], "confidence": 0.0}
        if the model doesn't return valid JSON.
    """
    await _ensure_session()

    # ── Inject per-turn steering instruction ───────────────────────────────────
    if steering is not None:
        root_agent.instruction = build_turn_instruction(steering)

    runner = Runner(
        app_name=_APP_NAME,
        agent=root_agent,
        session_service=_session_service,
    )

    # ── Stream the response ────────────────────────────────────────────────────
    raw_parts: list[str] = []
    async for event in runner.run_async(
        user_id=_USER_ID,
        session_id=_SESSION_ID,
        new_message=genai_types.Content(
            role="user",
            parts=[genai_types.Part(text=user_message)],
        ),
    ):
        if event.is_final_response() and event.content:
            for part in event.content.parts:
                if part.text:
                    raw_parts.append(part.text)

    raw_text = "".join(raw_parts).strip()

    # ── Parse expected JSON schema ─────────────────────────────────────────────
    try:
        # Strip markdown fences the model sometimes adds
        clean = raw_text.removeprefix("```json").removesuffix("```").strip()
        return json.loads(clean)
    except json.JSONDecodeError:
        return {"answer": raw_text, "citations": [], "confidence": 0.0}


# ── Interactive CLI loop ───────────────────────────────────────────────────────
async def _cli_loop() -> None:
    print("Policy Q&A agent ready.  Type 'quit' to exit.\n")

    # Example: first turn uses a tenant-scoped steering override
    first_turn = True

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in {"quit", "exit", "q"}:
            break
        if not user_input:
            continue

        # Demonstrate per-turn steering: EU tenant hint only on turn 1
        steering = None
        if first_turn:
            steering = SteeringInputs(
                goal="Answer the user's compliance question accurately.",
                style="concise",
                max_cites=2,
                tenant_hint="Answer for EU employees only.",
                confidence_range=(0.6, 0.9),
            )
            first_turn = False

        result = await run_turn(user_input, steering=steering)
        print(f"\nAgent: {json.dumps(result, indent=2)}\n")


if __name__ == "__main__":
    asyncio.run(_cli_loop())