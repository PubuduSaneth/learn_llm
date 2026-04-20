import asyncio
import os
import sys

from google.adk.runners import Runner
from google.genai import types

from policy_compliance_memory.agent import app, session_service

APP_NAME = app.name
USER_ID = os.getenv("ADK_USER_ID", "user")
SESSION_ID = os.getenv("ADK_SESSION_ID", "policy_compliance_memory_persistent")

async def ensure_session() -> None:
    existing = await session_service.get_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID,
    )
    if existing is None:
        await session_service.create_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=SESSION_ID,
            state={},
        )


async def run_once(user_message: str) -> str:
    await ensure_session()

    runner = Runner(
        app=app,
        session_service=session_service,
    )

    parts = []
    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=SESSION_ID,
        new_message=types.Content(
            role="user",
            parts=[types.Part(text=user_message)],
        ),
    ):
        if event.is_final_response() and event.content:
            for part in event.content.parts:
                if part.text:
                    parts.append(part.text)

    return "".join(parts).strip()


if __name__ == "__main__":
    message = " ".join(sys.argv[1:]).strip() or "Hello, remember my department is Legal Ops."
    response = asyncio.run(run_once(message))
    print(response)
    print(f"\n[session] app_name={APP_NAME} user_id={USER_ID} session_id={SESSION_ID}")
