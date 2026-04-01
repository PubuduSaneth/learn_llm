# Context Engineering with Google ADK
## A Practical Tutorial Using a Compliance Q&A Agent

---

## Introduction

Most LLM applications start with the same mistake: appending every message to a growing string and feeding it to the model. This "append-everything" strategy feels simple but creates two compounding problems as scale grows:

- **Latency spirals** — longer prompts mean slower and more expensive inference, every single turn.
- **"Lost in the middle" hallucinations** — models struggle to use information buried in the middle of very long contexts. The further a fact is from the beginning or end of the window, the less reliably the model retrieves it.

Google's Agent Development Kit (ADK) offers a principled alternative. Rather than treating context as a raw history dump, ADK treats it as a **compiled view**: a structured, durable session state from which a clean working context is dynamically derived each turn.

This tutorial walks through three scripts — `app_setup.py`, `steering.py`, and `chat_handler.py` — that together implement the four core ADK context engineering patterns. The example use case is a **compliance Q&A agent** for a fictional internal policy database.

---

## The Use Case: A Compliance Q&A Agent

The agent answers employee questions about internal compliance policies (e.g., ACME-42). It must:

- Return structured JSON with citations and a confidence score.
- Never invent policy numbers or provide medical/legal advice.
- Adapt its behaviour per-turn (style, tenant scope, citation count).
- Auto-correct itself if the previous response failed schema validation.

This is a realistic production scenario: a long, stable system prompt (the policy rules) combined with dynamic, per-turn steering that changes every request.

---

## Pattern 1 — Static vs. Turn Instructions (Context Caching)

**File: `app_setup.py`**

The first and most impactful pattern separates your system prompt into two distinct layers.

### The Problem

A typical system prompt is written once and sent in full on every request. If it is 2,000 tokens long and you handle 10,000 requests per day, you are paying for 20 million prompt tokens per day just to say the same thing over and over.

### The ADK Solution

ADK distinguishes between two types of instruction:

| Type | Description | Changes? |
|---|---|---|
| `static_instruction` | Invariant policies, schemas, safety rules, tool definitions | Never (or rarely) |
| `instruction` | Per-turn goal, style, tenant scope, corrective feedback | Every turn |

The `static_instruction` is eligible for **Context Caching**: ADK can compute its KV representation once and reuse it across many requests, so you only pay the full token cost on the first request (and after the TTL expires).

```python
# app_setup.py — the static header never changes between turns
STATIC_POLICY_HEADER = """You are a strict policy assistant for internal compliance Q&A.

Follow this exact JSON schema in every response:
{"answer": str, "citations": [str], "confidence": float}

Safety:
- Never provide medical or legal advice; refuse with a brief explanation.
- Never invent policy numbers or sections; ask for the missing reference.
...
"""

agent = Agent(
    name="policy_agent",
    static_instruction=STATIC_POLICY_HEADER,   # <-- cached
    instruction="Default: be concise and include at most two citations."  # <-- overridden per turn
)

app = App(
    name="policy_qa_app",
    context_cache_config=ContextCacheConfig(
        ttl_seconds=3600,   # keep the cached KV for 1 hour
        cache_intervals=5,  # force a refresh every 5 requests as a safety guardrail
        min_tokens=1000     # only bother caching if the header is large enough to be worth it
    ),
    root_agent=agent
)
```

### Why the Separation Also Improves Security

Because the static header is clearly marked as "controller-owned policy" and the turn instruction is separately composed by your application code, you gain a natural firewall. Prompt injection attacks that try to rewrite safety rules in the user's message cannot touch the cached static layer.

---

## Pattern 2 — Structured Turn Steering

**File: `steering.py`**

Rather than assembling turn instructions by string concatenation, ADK encourages you to treat turn steering as a **typed, structured object**. The `SteeringInputs` dataclass codifies every knob you might want to adjust at runtime.

```python
@dataclass
class SteeringInputs:
    goal: str                                  # what to accomplish this turn
    style: str = "concise"                     # terse, detailed, crisp, etc.
    max_cites: int = 2                         # how many citations to include
    tenant_hint: Optional[str] = None          # "Answer for EU employees only"
    corrective: Optional[str] = None           # feedback from the last failed turn
    confidence_range: Tuple[float, float] = (0.6, 0.9)
```

Each field maps directly to a control surface in the final prompt:

```python
def build_turn_instruction(s: SteeringInputs) -> str:
    parts = [
        f"Goal: {s.goal}",
        f"Style: {s.style}",
        (
            "Constraints: "
            f"include at most {s.max_cites} citations; "
            "refuse medical/legal advice; "
            "if info is missing, ask one targeted question; "
            f"return 'confidence' between {s.confidence_range[0]} and {s.confidence_range[1]}."
        )
    ]
    if s.tenant_hint:
        parts.append(f"Tenant: {s.tenant_hint}")
    if s.corrective:
        parts.append(f"Correction: {s.corrective}")
    return "\n".join(parts)
```

### Key Insight: Optional Fields for Conditional Context

Notice that `tenant_hint` and `corrective` are only appended when they are set. This means the working context grows only as large as it needs to be for a given turn. An EU-scoped query includes the tenant hint; a standard query does not. A turn following a failed validation includes the corrective; a first attempt does not.

This is **precision context**: the model receives exactly the steering it needs and nothing it doesn't.

---

## Pattern 3 — Controller-Owned Intent Routing

**File: `chat_handler.py`** (routing section)

The chat handler is responsible for translating raw user input into a structured goal that can be fed to `SteeringInputs`. This is done through a lightweight intent router.

```python
def route_intent(user_message: str) -> str:
    text = user_message.lower()
    if "compare" in text: return "compare"
    if "list" in text and "control" in text: return "list_controls"
    if "summarize" in text: return "summarize"
    return "answer"

INTENT_TO_GOAL = {
    "summarize": "Summarize ACME-42 in plain English.",
    "list_controls": "List mandatory controls from ACME-42 with one-line rationales.",
    "compare": "Compare ACME-42 to ISO 27001 at a high level, return a short markdown table inside the JSON 'answer'.",
    "answer": "Answer the user directly."
}
```

### Why This Matters for Context Engineering

Without intent routing, you pass the raw user message directly as the goal and rely on the model to infer what format and depth is appropriate. The model may or may not comply. With intent routing, the controller — your application code — makes that decision explicitly and encodes it as a structured directive.

The model's job is reduced from "figure out what to do and do it well" to "execute this well-defined goal." That is a much easier task, and it leads to more consistent, cacheable, and debuggable outputs.

---

## Pattern 4 — Closed-Loop Validation and Corrective Steering

**File: `chat_handler.py`** (validation section)

The most sophisticated pattern in these scripts is the feedback loop between validation and the next turn's steering.

```python
def chat(session_id: str, user_message: str, ui_style: str | None = None):
    intent = route_intent(user_message)
    goal = INTENT_TO_GOAL.get(intent, f"Answer the user: {user_message[:120]}")

    # Pull per-session state
    style = ui_style or get_flag(session_id, "style", default="concise")
    max_cites = get_flag(session_id, "max_citations", default=2)
    tenant_hint = get_tenant_hint(session_id)
    corrective = get_last_validation_error(session_id)  # None on first call

    # Build the turn instruction from structured state
    turn_instruction = build_turn_instruction(
        SteeringInputs(
            goal=goal,
            style=style,
            max_cites=max_cites,
            tenant_hint=tenant_hint,
            corrective=(
                f"Your last reply failed validation: {corrective}. Fix it this turn."
                if corrective else None
            )
        )
    )

    agent.instruction = turn_instruction
    response = agent.run(user_message=user_message)

    # Validate the response, store any error for the next turn
    validate_and_record(session_id, response)
    return response
```

### The Corrective Feedback Loop in Plain Terms

1. Turn N runs, the response fails JSON schema validation (e.g., `confidence` field missing).
2. `validate_and_record` stores the error string against `session_id`.
3. Turn N+1: `get_last_validation_error` retrieves that string.
4. `build_turn_instruction` appends it as a `Correction:` directive.
5. The model receives a precise, actionable instruction to fix the specific field it missed.

This is far more effective than hoping the model will spontaneously improve. The controller acts as a QA layer that writes corrective instructions back into the context pipeline, creating a self-healing loop.

---

## How the Three Files Work Together

```
                         ┌─────────────────────────────────┐
                         │         app_setup.py             │
                         │  static_instruction (cached)     │
                         │  ContextCacheConfig (TTL, etc.)  │
                         └────────────────┬────────────────┘
                                          │  agent object
                         ┌────────────────▼────────────────┐
                         │         chat_handler.py          │
                         │  route_intent → goal             │
                         │  get session flags               │
                         │  get corrective feedback         │
                         │         │                        │
                         │  ┌──────▼──────┐                 │
                         │  │ steering.py │                 │
                         │  │ SteeringInputs                │
                         │  │ build_turn_instruction        │
                         │  └──────┬──────┘                 │
                         │         │  turn instruction       │
                         │  agent.instruction = ...         │
                         │  agent.run(user_message)         │
                         │  validate_and_record             │
                         └─────────────────────────────────┘
```

Each file has a single, clear responsibility:

- `app_setup.py` — defines what never changes (static context + caching policy).
- `steering.py` — defines how to express what changes (structured turn instructions).
- `chat_handler.py` — orchestrates the two at runtime, adding routing, session state, and validation feedback.

---

## Minimal Working Example

To try the pattern with the simplest possible setup, you need five things:

**1. Install the SDK**
```bash
pip install google-adk
```

**2. Copy the three files into your project**
```
my_agent/
├── app_setup.py
├── steering.py
└── chat_handler.py
```

**3. Stub out the session helpers in `chat_handler.py`**

Replace the three helper calls with in-memory stubs for local testing:

```python
_session_store = {}

def get_flag(session_id, key, default=None):
    return _session_store.get(session_id, {}).get(key, default)

def get_tenant_hint(session_id):
    return None  # no tenant scoping for local test

def get_last_validation_error(session_id):
    return _session_store.get(session_id, {}).get("last_error", None)

def validate_and_record(session_id, response):
    import json
    try:
        data = json.loads(response)
        required = {"answer", "citations", "confidence"}
        missing = required - data.keys()
        if missing:
            _session_store.setdefault(session_id, {})["last_error"] = f"Missing fields: {missing}"
        else:
            _session_store.setdefault(session_id, {}).pop("last_error", None)
    except json.JSONDecodeError:
        _session_store.setdefault(session_id, {})["last_error"] = "Response was not valid JSON"
```

**4. Run a simple two-turn conversation**

```python
# run_test.py
from chat_handler import chat

session = "test-session-001"

# Turn 1: normal query
response = chat(session, "Summarize ACME-42")
print("Turn 1:", response)

# Simulate a validation failure (as if turn 1 returned bad JSON)
_session_store[session]["last_error"] = "Missing 'confidence' field"

# Turn 2: the corrective directive is now injected automatically
response = chat(session, "Summarize ACME-42")
print("Turn 2 (with correction):", response)
```

**5. Observe the difference in turn instructions**

Add a print statement before `agent.run` in `chat_handler.py`:

```python
print("--- TURN INSTRUCTION ---")
print(turn_instruction)
print("------------------------")
```

Turn 1 output will look like:
```
Goal: Summarize ACME-42 in plain English.
Style: concise
Constraints: include at most 2 citations; refuse medical/legal advice; ...
```

Turn 2 output (with corrective) will look like:
```
Goal: Summarize ACME-42 in plain English.
Style: concise
Constraints: include at most 2 citations; refuse medical/legal advice; ...
Correction: Your last reply failed validation: Missing 'confidence' field. Fix it this turn.
```

The static header from `app_setup.py` is sent to the model separately (and cached), so you never see it here — that separation is the whole point.

---

## Summary: The Four Patterns

| Pattern | Where | What It Solves |
|---|---|---|
| Static vs. Turn Instructions | `app_setup.py` | Latency and cost from re-sending invariant content |
| Structured Turn Steering | `steering.py` | Ad-hoc string assembly, hard-to-debug turn instructions |
| Controller-Owned Intent Routing | `chat_handler.py` | Models inferring format/depth from raw user messages |
| Closed-Loop Corrective Feedback | `chat_handler.py` | Schema drift, unreliable output structure |

Together, these patterns shift the mental model from "send everything and hope" to "compile a precise working context from durable structured state." That shift is what makes the difference between a prototype and a production-grade agent.
