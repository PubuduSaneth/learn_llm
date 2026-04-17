# Goodmem Embedder Auth Fix (Exact Sequence)

This checklist is for your current local Docker Goodmem setup where retrieval fails with:

- Multiple authentication credentials received. Please pass only one.

Current symptoms this fixes:

1. Memory save calls appear successful.
2. Memory records end in processingStatus FAILED.
3. Retrieval returns no chunks.

## Goal

Create a clean embedder and clean space using exactly one authentication path, then pin those IDs in agent configuration.

## Prerequisites

1. Goodmem Docker services are running.
2. Your agent .env file exists at [content/Agent_tutorials/Hands-on/D5_s2/policy_compliance_memory/.env](content/Agent_tutorials/Hands-on/D5_s2/policy_compliance_memory/.env).
3. You have one valid Gemini API key.

## Step 1: Back up current .env

From [content/Agent_tutorials/Hands-on](content/Agent_tutorials/Hands-on):

    cp D5_s2/policy_compliance_memory/.env D5_s2/policy_compliance_memory/.env.backup

## Step 2: Normalize agent-side env variables

Edit [content/Agent_tutorials/Hands-on/D5_s2/policy_compliance_memory/.env](content/Agent_tutorials/Hands-on/D5_s2/policy_compliance_memory/.env) to keep only one Gemini key variable for now.

Keep:

1. GOODMEM_API_KEY
2. GOODMEM_BASE_URL
3. GOODMEM_DEBUG
4. GOOGLE_API_KEY

Temporarily remove or comment:

1. GOODMEM_EMBEDDER_ID
2. GOODMEM_SPACE_ID
3. GOODMEM_SPACE_NAME
4. GEMINI_API_KEY (if present)
5. Any duplicate alternate key vars you are not actively using

Use this minimal shape:

    export GOODMEM_API_KEY="<goodmem-api-key>"
    export GOODMEM_BASE_URL="https://localhost:8080"
    export GOODMEM_DEBUG="true"
    export GOOGLE_API_KEY="<one-gemini-key-only>"

Why:

- Prevents mixed credential sources while creating a fresh embedder path.

## Step 3: Verify Goodmem server health and logs

From repo root [content/Agent_tutorials/Hands-on](content/Agent_tutorials/Hands-on):

    docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'

    docker logs --tail 80 goodmem-goodmem-1-server

Expected:

1. Server container healthy.
2. No startup errors.

## Step 4: Create a fresh embedder and fresh space

Run this helper from [content/Agent_tutorials/Hands-on](content/Agent_tutorials/Hands-on):

```bash
    uv run python - <<'PY'
    import json
    import os
    import uuid
    from pathlib import Path

    import httpx
    from dotenv import load_dotenv
    from goodmem_adk.client import GoodmemClient

    # Match your current local TLS behavior
    _orig = httpx.Client
    class UnverifiedClient(_orig):
        def __init__(self, *args, **kwargs):
            kwargs['verify'] = False
            super().__init__(*args, **kwargs)
    httpx.Client = UnverifiedClient

    load_dotenv(Path('D5_s2/policy_compliance_memory/.env'))

    base = os.getenv('GOODMEM_BASE_URL')
    key = os.getenv('GOODMEM_API_KEY')
    google_api_key = os.getenv('GOOGLE_API_KEY')

    if not base or not key or not google_api_key:
        raise SystemExit('Missing GOODMEM_BASE_URL, GOODMEM_API_KEY, or GOOGLE_API_KEY')

    client = GoodmemClient(base, key)

    # 1) create new embedder (single auth source: inline API key)
    embedder = client.create_embedder(
        display_name='gemini-embedding-001-clean',
        provider_type='OPENAI',
        endpoint_url='https://generativelanguage.googleapis.com/v1beta/openai',
        model_identifier='gemini-embedding-001',
        dimensionality=1536,
        api_key=google_api_key,
        distribution_type='DENSE',
    )
    embedder_id = embedder['embedderId']

    # 2) create new space pinned to that embedder
    space_name = f'policy_compliance_memory_clean_{uuid.uuid4().hex[:8]}'
    space = client.create_space(space_name=space_name, embedder_id=embedder_id)
    space_id = space['spaceId']

    print(json.dumps({'embedder_id': embedder_id, 'space_id': space_id, 'space_name': space_name}, indent=2))
    PY
```

Capture the printed values.

## Step 5: Pin embedder and space in .env

Update [content/Agent_tutorials/Hands-on/D5_s2/policy_compliance_memory/.env](content/Agent_tutorials/Hands-on/D5_s2/policy_compliance_memory/.env):

    export GOODMEM_EMBEDDER_ID="<new-embedder-id-from-step-4>"
    export GOODMEM_SPACE_ID="<new-space-id-from-step-4>"
    export GOODMEM_SPACE_NAME="<new-space-name-from-step-4>"

Notes:

1. Keep both SPACE_ID and SPACE_NAME initially for explicit validation.
2. They must refer to the same space.

## Step 6: Restart runtime cleanly

1. Stop all running adk web processes.
2. Restart Goodmem server only if you changed server env.
3. Run fresh test turn with your runner:

    uv run python D5_s2/run_with_persistent_session.py "Remember my department is Legal Ops."

4. Run recall turn:

    uv run python D5_s2/run_with_persistent_session.py "What is my department?"

## Step 7: Validate memory processing status is SUCCEEDED

Use the latest memory id from debug logs (or query recent memories if you have tooling) and check status:

```bash
    uv run python - <<'PY'
    import json
    import os
    from pathlib import Path

    import httpx
    from dotenv import load_dotenv
    from goodmem_adk.client import GoodmemClient

    _orig = httpx.Client
    class UnverifiedClient(_orig):
        def __init__(self, *args, **kwargs):
            kwargs['verify'] = False
            super().__init__(*args, **kwargs)
    httpx.Client = UnverifiedClient

    load_dotenv(Path('D5_s2/policy_compliance_memory/.env'))
    client = GoodmemClient(os.getenv('GOODMEM_BASE_URL'), os.getenv('GOODMEM_API_KEY'))

    memory_id = '<replace-with-recent-memory-id>'
    m = client.get_memory_by_id(memory_id)
    print(json.dumps({'memoryId': m.get('memoryId'), 'processingStatus': m.get('processingStatus')}, indent=2))
    PY
```

Expected:

1. processingStatus should be SUCCEEDED.
2. Retrieval should return chunks for related queries.

## Step 8: If still failing, isolate server credential mixing

Check Goodmem server env for conflicting key injection:

    docker inspect goodmem-goodmem-1-server --format '{{json .Config.Env}}'

Look for any provider key env vars that might overlap embedder inline credentials.

If present, choose one strategy and remove the other:

1. Inline-only embedder credentials (recommended for this setup).
2. Server-env-only credentials (advanced; requires consistent provider mapping).

Then recreate embedder and space again.

## Safe Rollback

If you need to revert:

    cp D5_s2/policy_compliance_memory/.env.backup D5_s2/policy_compliance_memory/.env

## Final Verification Matrix

1. Runner path:
   - Save turn works.
   - Recall turn returns saved facts.

2. ADK web path with explicit session/artifact URIs:
   - Same thread preserves ADK session context.
   - Goodmem retrieval returns relevant chunks.

3. Backend:
   - No new Multiple authentication credentials received errors in server logs.
