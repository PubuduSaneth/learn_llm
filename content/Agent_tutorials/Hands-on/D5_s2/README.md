# D5_s2 Persistent Memory Guide

This folder contains a policy compliance agent that uses two persistence layers:

1. ADK session persistence via SQLite (`DatabaseSessionService`)
2. Long-term semantic memory via Goodmem (`GoodmemPlugin`, `GoodmemFetchTool`, `GoodmemSaveTool`)

## Files

- `policy_compliance_memory/agent.py`
  - Defines the `compliance_specialist` agent
  - Loads environment variables from `policy_compliance_memory/.env`
  - Configures Goodmem plugin and Goodmem tools
  - Exports:
    - `app` (ADK App)
    - `my_agent` (root agent used by runner)
    - `session_service` (`DatabaseSessionService`)

- `run_with_persistent_session.py`
  - Tiny runtime script that runs `Runner(app=app, session_service=session_service)`
  - Ensures session creation/reuse with fixed app/user/session IDs
  - Sends one user message and prints final response

## How Persistence Works

### 1) ADK session persistence (SQLite)

In `policy_compliance_memory/agent.py`:

- `session_service = DatabaseSessionService(db_url=f"sqlite+aiosqlite:///{Path(__file__).with_name('agent_history.db')}")`

The runner uses this object explicitly and runs with `app`:

- `Runner(app=app, session_service=session_service)`

This guarantees that ADK conversation session state uses a stable SQLite file path in the execution path.

### 2) Goodmem long-term memory

In `policy_compliance_memory/agent.py`:

- `GoodmemPlugin(...)` attached to `App(..., plugins=[persistent_memory])`
- `GoodmemFetchTool(...)` and `GoodmemSaveTool(...)` attached to the agent tools
- Optional pinning is supported via environment variables:
  - `GOODMEM_EMBEDDER_ID`
  - `GOODMEM_SPACE_ID`
  - `GOODMEM_SPACE_NAME`

This gives the model both:

- passive memory capture/injection via plugin callbacks
- explicit save/fetch tool calls from the model

## Required Environment

Create/update `policy_compliance_memory/.env`:

```env
export GOODMEM_API_KEY="<your-key>"
export GOODMEM_BASE_URL="https://localhost:8080"
export GOODMEM_SPACE_NAME="policy_compliance_memory_test"
export GOODMEM_DEBUG="true"
export GOODMEM_EMBEDDER_ID="<optional-fixed-embedder-id>"
export GOODMEM_SPACE_ID="<optional-fixed-space-id>"
```

Notes:

- Keep one fixed `GOODMEM_SPACE_NAME` across runs if you want cross-session recall.
- If you provide `GOODMEM_SPACE_ID`, it takes precedence over name-based space resolution.
- Current local Goodmem setup in this project is HTTPS on port 8080.

## Root Cause and Fix Summary

Persistent memory was failing due to multiple independent issues:

1. Runner execution path did not guarantee App-level plugins were active.
2. ADK session DB setup needed async SQLite dependencies and URL shape.
3. Relative DB URL caused confusion about where the SQLite file was created.
4. Goodmem retrieval failed because backend memory processing failed (`processingStatus=FAILED`) due to embedder authentication conflicts.

What changed in code to fix this:

1. Runner now uses `Runner(app=app, session_service=session_service)`.
2. Session service uses async SQLite and module-local absolute path.
3. Dependencies were updated for async SQLAlchemy sessions (`greenlet`, `aiosqlite`).
4. Goodmem config now supports fixed embedder/space IDs to avoid auto-resolution issues in unstable environments.

Why this helps:

1. App plugin callbacks are guaranteed to run in the tested path.
2. Session state is persisted to one predictable SQLite file.
3. Goodmem save/fetch calls can be pinned to known-good space/embedder settings.
4. Debug logs (`GOODMEM_DEBUG=true`) make callback failures immediately visible.

Important backend note:

- If Goodmem memories show `processingStatus=FAILED` with messages like:
  - `Multiple authentication credentials received. Please pass only one.`
- then retrieval will return zero chunks even though save calls succeed.
- This must be fixed in Goodmem embedder configuration/server auth; it is not a Python-side logic bug.

## Run the Persistent Session Runner

From `content/Agent_tutorials/Hands-on`:

```bash
uv run python D5_s2/run_with_persistent_session.py "Remember my department is Legal Ops."
uv run python D5_s2/run_with_persistent_session.py "What is my department?"
```

Before first run (or after dependency updates):

```bash
uv sync
```

Optional overrides:

- `ADK_USER_ID`
- `ADK_SESSION_ID`

Example:

```bash
ADK_USER_ID=user ADK_SESSION_ID=demo_session uv run python D5_s2/run_with_persistent_session.py "My role is Compliance Lead."
ADK_USER_ID=user ADK_SESSION_ID=demo_session uv run python D5_s2/run_with_persistent_session.py "What is my role?"
```

## Run with Google ADK Web (Correct Command)

From `content/Agent_tutorials/Hands-on/D5_s2` run:

```bash
uv run adk web . --no-reload \
  --session_service_uri "sqlite:////Users/pubuduss/Developer/com/learn_llm/content/Agent_tutorials/Hands-on/D5_s2/.adk/web_sessions.db" \
  --artifact_service_uri "file:///Users/pubuduss/Developer/com/learn_llm/content/Agent_tutorials/Hands-on/D5_s2/.adk/artifacts"
```

Why this command matters:

1. It forces ADK Web to use a persistent SQLite session backend.
2. It forces ADK Web artifacts to a persistent local folder.
3. It removes ambiguity from ADK defaults that can vary by runtime and writability.

### Why `uv run adk web . --no-reload` can fail to provide persistent memory

Using only:

```bash
uv run adk web . --no-reload
```

can be inconsistent for persistence in this setup because:

1. ADK Web manages its own runtime session service unless explicitly pinned by CLI URI.
2. The exported `session_service` object in `policy_compliance_memory/agent.py` is not automatically injected into ADK Web runtime service selection.
3. If ADK resolves to in-memory/default storage in your environment, session continuity across restarts/new sessions is lost.

In short: the explicit `--session_service_uri` and `--artifact_service_uri` flags make persistence deterministic.

## Verify Session DB Persistence

The SQLite DB is created when the runner actually executes and uses `session_service`.

The DB path is now module-local (`D5_s2/policy_compliance_memory/agent_history.db`), so check:

```bash
ls -l D5_s2/policy_compliance_memory/agent_history.db
sqlite3 D5_s2/policy_compliance_memory/agent_history.db ".tables"
```

For ADK Web mode, verify the web session DB:

```bash
ls -l D5_s2/.adk/web_sessions.db
sqlite3 D5_s2/.adk/web_sessions.db ".tables"
```

## Troubleshooting

### `ValueError: Failed to create database engine for URL 'sqlite:///...'`

Use async SQLite URL with ADK session service:

- `sqlite+aiosqlite:///agent_history.db`

### Memory not recalled across sessions

Check all of these:

1. Same `GOODMEM_SPACE_NAME` is used across runs.
2. Goodmem server is reachable.
3. `GOODMEM_DEBUG=true` to inspect callback behavior.
4. Use the same `ADK_USER_ID`/`ADK_SESSION_ID` when testing session continuity.
5. Confirm memory processing is not failing in Goodmem backend (failed processing means retrieval returns empty).

### Goodmem retrieval returns no chunks

If logs show `processingStatus=FAILED` or `All embedding attempts failed`, inspect Goodmem server logs and fix embedder auth configuration.
When this backend issue exists, memory save can appear to work but retrieval remains empty.
