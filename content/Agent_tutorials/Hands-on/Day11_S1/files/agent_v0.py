from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import (
    StreamableHTTPConnectionParams,
    StdioConnectionParams,
)
from mcp import StdioServerParameters
import os

# ── Tool 1: BigQuery via remote managed MCP server (HTTPS + OAuth)
def get_bigquery_toolset():
    credentials, project_id = google.auth.default(
        scopes=["https://www.googleapis.com/auth/bigquery"]
    )
    credentials.refresh(google.auth.transport.requests.Request())
    return McpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url="https://bigquery.googleapis.com/mcp",
            headers={
                "Authorization": f"Bearer {credentials.token}",
                "x-goog-user-project": project_id,
            },
        ),
        tool_filter=["execute_query", "list_datasets", "get_table_info"],
    )

# ── Tool 2: Google Maps via npx subprocess (stdio transport)
def get_maps_toolset():
    return McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command="npx",
                args=["-y", "@modelcontextprotocol/server-google-maps"],
                env={"GOOGLE_MAPS_API_KEY": os.getenv("MAPS_API_KEY")},
            )
        ),
        tool_filter=["search_places", "get_directions"],
    )

# ── Agent uses both toolsets — agent decides at runtime which to call
root_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="bakery_scout",
    instruction="...",
    tools=[get_bigquery_toolset(), get_maps_toolset()],  # two servers!
)