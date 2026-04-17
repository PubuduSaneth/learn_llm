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
  - Tiny runtime script that explicitly passes `session_service` into `Runner`
  - Ensures session creation/reuse with fixed app/user/session IDs
  - Sends one user message and prints final response

## How Persistence Works

### 1) ADK session persistence (SQLite)

In `policy_compliance_memory/agent.py`:

- `session_service = DatabaseSessionService(db_url="sqlite+aiosqlite:///agent_history.db")`

The runner uses this object explicitly:

- `Runner(..., session_service=session_service)`

This guarantees that ADK conversation session state uses the SQLite DB in the execution path.

### 2) Goodmem long-term memory

In `policy_compliance_memory/agent.py`:

- `GoodmemPlugin(...)` attached to `App(..., plugins=[persistent_memory])`
- `GoodmemFetchTool(...)` and `GoodmemSaveTool(...)` attached to the agent tools

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
```

Notes:

- Keep one fixed `GOODMEM_SPACE_NAME` across runs if you want cross-session recall.
- Current local Goodmem setup in this project is HTTPS on port 8080.

## Run the Persistent Session Runner

From `content/Agent_tutorials/Hands-on`:

```bash
uv run python D5_s2/run_with_persistent_session.py "Remember my department is Legal Ops."
uv run python D5_s2/run_with_persistent_session.py "What is my department?"
```

Optional overrides:

- `ADK_USER_ID`
- `ADK_SESSION_ID`

Example:

```bash
ADK_USER_ID=user ADK_SESSION_ID=demo_session uv run python D5_s2/run_with_persistent_session.py "My role is Compliance Lead."
ADK_USER_ID=user ADK_SESSION_ID=demo_session uv run python D5_s2/run_with_persistent_session.py "What is my role?"
```

## Verify Session DB Persistence

The SQLite DB is created when the runner actually executes and uses `session_service`.

Because the DB URL is relative, the file is created in your process working directory.
If you run from `content/Agent_tutorials/Hands-on`, check:

```bash
ls -l agent_history.db
sqlite3 agent_history.db ".tables"
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

### DB file not found in `D5_s2`

If you launched from a different folder, the relative DB path may resolve elsewhere.
Run from `content/Agent_tutorials/Hands-on` to keep location predictable.
