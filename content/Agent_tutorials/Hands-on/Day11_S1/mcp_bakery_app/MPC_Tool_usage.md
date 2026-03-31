# MCP Integration Notes

## Maps MCP Integration

- The Bakery Location Intelligence Agent wires up the Google Maps MCP toolset once at import time so every request reuses the same connection (agent.py). That shared `maps_toolset` is injected into `root_agent` alongside the BigQuery tools, giving Gemini a single consolidated tool surface (agent.py).

### Authentication & Connectivity

- The Maps MCP endpoint is hard-coded as `https://mapstools.googleapis.com/mcp`, matching Google’s managed MCP server (tools.py).
- `get_maps_mcp_toolset()` loads environment variables (via `dotenv`) and expects `MAPS_API_KEY`; the key is forwarded through the `x-goog-api-key` header in every MCP call, so no OAuth exchange is required for Maps (tools.py).
- Because `StreamableHTTPConnectionParams` is used, the agent can stream partial responses (directions steps, etc.) from the remote Maps MCP server, and the helper logs a confirmation once the toolset is ready (tools.py).

### Tool Surface Available to the Agent

- Documentation inside `get_maps_mcp_toolset()` enumerates the primary Maps MCP tools the agent can call: `maps_search_places`, `maps_geocode`, `maps_reverse_geocode`, `maps_distance_matrix`, and `maps_directions`, covering discovery, geocoding, and routing workflows (tools.py).
- Because the agent receives the entire `maps_toolset`, Gemini can dynamically pick any of these functions based on the conversation, rather than hard-coding individual calls.

### How the LLM Is Instructed to Use Maps

- The prompt dedicates a full section to the “MAPS TOOLSET — real-world location intelligence,” clarifying when to lean on Google Maps: competitive scans, geocoding, travel-time calculations, and saturation checks (agent.py).
- The agent must embed an interactive Google Maps hyperlink whenever sharing location-based findings, guaranteeing users can inspect the referenced area directly (agent.py).
- Every final recommendation is required to blend at least one Maps observation with two BigQuery data points, forcing the LLM to cross-validate demographic analytics against the physical-world context delivered by the Maps MCP tools (agent.py).

### Operational Workflow

- Startup steps: developers must supply `MAPS_API_KEY` (for Maps) and run `gcloud auth application-default login` (for BigQuery) before launching `adk web`, ensuring both MCP sessions authenticate correctly (tools.py and agent.py).
- Once the toolsets are initialized, `root_agent` (Gemini 3 Flash) can autonomously call Maps MCP functions as the conversation demands, satisfying the instruction hierarchy without any additional glue code.

## BigQuery MCP toolsets integration

### Purpose & Context

- The Bakery Location Intelligence Agent runs as `root_agent` using Gemini 3 Flash and wires in both Maps and BigQuery MCP toolsets at import time so each conversation can call either surface seamlessly (agent.py). 
- BigQuery provides the structured datasets (`mcp_bakery.demographics`, `foot_traffic`, `bakery_prices`, `sales_history_weekly`) that the LLM must reference whenever it makes recommendations (agent.py).

### Toolset Initialization

- `tools.get_bigquery_mcp_toolset()` is executed at module load, producing a reusable `McpToolset` instance built from `StreamableHTTPConnectionParams` aimed at Google’s managed BigQuery MCP endpoint `https://bigquery.googleapis.com/mcp` (tools.py).  
- The helper uses Application Default Credentials (`google.auth.default`) with the BigQuery scope, refreshes the token immediately, then injects the bearer token plus `x-goog-user-project` header so billing lands in the detected project (tools.py).  
- A console message confirms configuration, which helps operators verify that the MCP session is ready before the agent begins serving requests (tools.py).

### Authentication Workflow

- Developers must run `gcloud auth application-default login` prior to launching the agent to seed ADC credentials; the code assumes this and fails gracefully only if credentials cannot be loaded (tools.py).  
- Token lifetime is ~60 minutes; comments instruct restarting `adk web` post re-authentication to avoid expiry mid-session (tools.py).  
- agent.py also sets `GOOGLE_CLOUD_PROJECT`/`GOOGLE_CLOUD_LOCATION` environment variables using the same ADC discovery, keeping Vertex AI + BigQuery aligned to the authenticated project (agent.py).

### BigQuery Tools Available via MCP

- The inline documentation lists the primary methods surfaced by the BigQuery MCP server: `list_dataset_ids`, `get_dataset_info`, `list_table_ids`, `get_table_info`, and `execute_sql`. These appear automatically in the toolset returned to the LLM (tools.py).  
- Because the MCP server is remote and managed by Google, the application does not host or maintain any additional infrastructure—it simply connects over HTTPS with the appropriate headers.

### Prompt-Level Usage Requirements

- The system prompt enforces a disciplined workflow: confirm datasets via `get_dataset_info`, inspect schemas via `get_table_info`, then run SQL through `execute_sql`, retrying after errors (agent.py).  
- When formulating answers, the agent must cite at least two data points drawn from the BigQuery tables and combine them with a Maps observation, ensuring every recommendation is grounded in structured analytics (agent.py).  
- Table descriptions inside the prompt clarify how each dataset supports the bakery siting decision (demographics, competition pricing, historical sales, temporal foot traffic), guiding the LLM toward relevant queries (agent.py).

### Operational Summary

- Startup: ensure ADC credentials exist, load `.env`, and launch `adk web`.  
- Runtime: Gemini selects BigQuery tools through the MCP interface to inspect datasets or execute SQL; responses stream back through the `StreamableHTTPConnectionParams` channel.  
- Outputs: every user-facing answer pairs quantitative BigQuery findings with qualitative Maps intelligence, fulfilling the cross-data mandate baked into the agent prompt.

No code changes were required; this document captures how the existing agent.py and tools.py coordinate BigQuery MCP usage.
