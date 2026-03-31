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