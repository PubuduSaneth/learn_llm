"""
tools.py
--------
MCP toolset factory functions for the Bakery Location Agent.

Two remote Google-managed MCP servers are used:
  - BigQuery MCP  : https://bigquery.googleapis.com/mcp
  - Maps MCP      : https://mapstools.googleapis.com/mcp

Authentication
  - BigQuery uses Application Default Credentials (ADC).
    Run once before starting the agent:
        gcloud auth application-default login
  - Maps uses a plain API key injected as an X-Goog-Api-Key header.
    Set MAPS_API_KEY in your .env file.
"""

import os

import dotenv
import google.auth
import google.auth.transport.requests

from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams

# ── MCP server endpoints (Google-managed, no infra to run) ──────────────────
BIGQUERY_MCP_URL = "https://bigquery.googleapis.com/mcp"
MAPS_MCP_URL     = "https://mapstools.googleapis.com/mcp"


# ── Maps toolset ─────────────────────────────────────────────────────────────

def get_maps_mcp_toolset() -> McpToolset:
    """
    Connect to the Google Maps Platform MCP server.

    Auth: API key passed as X-Goog-Api-Key header.
    The MAPS_API_KEY env var must be set in .env (or the shell environment).

    Tools exposed by this server (selection):
      - maps_search_places      : find businesses / POIs near a location
      - maps_geocode            : convert address → lat/lng
      - maps_reverse_geocode    : convert lat/lng → address
      - maps_distance_matrix    : travel time / distance between points
      - maps_directions         : step-by-step routing
    """
    dotenv.load_dotenv()
    maps_api_key = os.getenv("MAPS_API_KEY", "no_api_key_found")

    toolset = McpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url=MAPS_MCP_URL,
            headers={
                "X-Goog-Api-Key": maps_api_key,
            },
        )
    )
    print("✅ Maps MCP toolset configured (Streamable HTTP).")
    return toolset


# ── BigQuery toolset ──────────────────────────────────────────────────────────

def get_bigquery_mcp_toolset() -> McpToolset:
    """
    Connect to the Google BigQuery MCP server using Application Default Credentials.

    Auth: OAuth 2.0 Bearer token generated from ADC, refreshed on every call
    so the agent always starts with a valid token.
    Also passes x-goog-user-project so BigQuery bills the correct project.

    ⚠  Token lifetime is ~60 min. If adk web runs longer, restart the agent
       after re-authenticating:  gcloud auth application-default login

    Tools exposed by this server (selection):
      - bigquery_list_datasets   : list all datasets in the project
      - bigquery_list_tables     : list tables in a dataset
      - bigquery_get_table_info  : describe schema + sample rows
      - bigquery_execute_query   : run a SQL query and return results
    """
    credentials, project_id = google.auth.default(
        scopes=["https://www.googleapis.com/auth/bigquery"]
    )

    # Force a refresh so the token is valid at agent startup
    credentials.refresh(google.auth.transport.requests.Request())
    oauth_token = credentials.token

    toolset = McpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url=BIGQUERY_MCP_URL,
            headers={
                "Authorization":     f"Bearer {oauth_token}",
                "x-goog-user-project": project_id,
            },
        )
    )
    print("✅ BigQuery MCP toolset configured (Streamable HTTP).")
    return toolset
