# Bakery Location Intelligence Agent
### Google ADK + BigQuery MCP + Google Maps MCP

An AI agent that helps you decide **where to open a bakery in Los Angeles**
by combining structured demographic/sales data from BigQuery with real-world
location intelligence from Google Maps — both accessed via MCP.

---

## Project Structure

```
bakery_agent/                    ← run `adk web .` from here
├── mcp_bakery_app/
│   ├── __init__.py              ← makes this an ADK-discoverable package
│   ├── agent.py                 ← LlmAgent definition (edit instructions here)
│   ├── tools.py                 ← MCP toolset factories (BigQuery + Maps)
│   ├── .env.example             ← copy to .env and fill in your keys
│   └── .env                     ← your actual secrets (never commit)
├── data/
│   ├── bakery_prices.csv        ← competitor pricing in LA Metro
│   ├── demographics.csv         ← zip-level census + foot-traffic index
│   ├── foot_traffic.csv         ← foot traffic by zip and time of day
│   └── sales_history_weekly.csv ← weekly sales by store and product
└── setup/
    └── setup_bigquery.sh        ← one-shot script: creates BQ dataset + loads CSVs
```

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.10+ | |
| `gcloud` CLI | [Install guide](https://cloud.google.com/sdk/docs/install) |
| Google Cloud project with billing | |
| Gemini API key | [Get one at AI Studio](https://aistudio.google.com/apikey) |
| Google Maps Platform API key | Enable: Places API, Directions API, Distance Matrix API |

---

## Setup (5 steps)

### Step 1 — Authenticate with Google Cloud

```bash
gcloud auth application-default login
export GOOGLE_CLOUD_PROJECT=your-project-id
gcloud config set project $GOOGLE_CLOUD_PROJECT
```

### Step 2 — Load data into BigQuery

```bash
cd bakery_agent/
chmod +x setup/setup_bigquery.sh
./setup/setup_bigquery.sh
```

This script:
- Enables the BigQuery API
- Creates the `mcp_bakery` dataset (US region)
- Loads all four CSV tables with auto-detected schemas

### Step 3 — Install the ADK

```bash
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install google-adk google-auth python-dotenv
```

### Step 4 — Configure environment

```bash
cp mcp_bakery_app/.env.example mcp_bakery_app/.env
# Edit .env and fill in:
#   GOOGLE_CLOUD_PROJECT   your GCP project ID
#   GOOGLE_API_KEY         Gemini API key from AI Studio
#   MAPS_API_KEY           Google Maps Platform API key
```

### Step 5 — Run the agent

```bash
# From the bakery_agent/ directory (parent of mcp_bakery_app/)
adk web .
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000), select **root_agent**
from the dropdown, and start chatting.

---

## Sample Questions

Try these to exercise both MCP tools together:

**Foot traffic + demographics:**
> "I want to open a bakery in Los Angeles. Find the zip code with the highest
> morning foot traffic score."

**Competition analysis:**
> "Can you search for bakeries in that zip code to see if it's saturated?"

**Pricing strategy:**
> "What is the maximum price being charged for a Sourdough Loaf in the
> LA Metro area? Is there a premium organic tier?"

**Revenue projection:**
> "Look at my sales history. Which store location sells the most Sourdough
> Loaf by revenue? Project what that store would earn in December 2025."

**Logistics:**
> "Find the closest Restaurant Depot to zip code 90004 and tell me the
> driving time for daily restocking."

**Combined recommendation:**
> "Give me your top recommendation for a new bakery location in LA,
> combining demographic data, foot traffic, competition, and pricing."

---

## How It Works

```
User prompt
    │
    ▼
LlmAgent (gemini-2.0-flash)
    │  reasons about which tool to call
    ├──► McpToolset (BigQuery MCP)
    │       │  StreamableHTTP → https://bigquery.googleapis.com/mcp
    │       │  Auth: OAuth Bearer token (from gcloud ADC)
    │       └──► runs SQL → returns rows
    │
    └──► McpToolset (Maps MCP)
             │  StreamableHTTP → https://maps.googleapis.com/mcp/v1
             │  Auth: X-Goog-Api-Key header
             └──► places search / routing → returns JSON
```

### Key files explained

**`tools.py`** — Two factory functions, one per MCP server:
- `get_bigquery_mcp_toolset()` — refreshes an OAuth token from ADC and
  connects to the BigQuery MCP endpoint
- `get_maps_mcp_toolset()` — passes a Maps API key in a header and connects
  to the Maps MCP endpoint

**`agent.py`** — Calls both factories at module load time, then defines the
`root_agent` with detailed instructions about which tool to use for which
type of question.

---

## Notes

- **Token expiry**: BigQuery OAuth tokens last ~60 min. If the agent starts
  returning auth errors, re-run `gcloud auth application-default login` and
  restart `adk web`.
- **Model**: The original codelab uses `gemini-3.1-pro-preview`. This project
  defaults to `gemini-2.0-flash` (stable). Change the `model=` field in
  `agent.py` if you have access to a newer preview model.
- **Maps APIs to enable**: Places API (New), Directions API, Distance Matrix
  API, Geocoding API — all under your Maps API key's restrictions.
