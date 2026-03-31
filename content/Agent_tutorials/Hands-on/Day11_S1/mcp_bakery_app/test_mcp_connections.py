import asyncio
from tools import get_maps_mcp_toolset, get_bigquery_mcp_toolset

async def get_tools_safely(toolset):
    """Attempts to find the tool list using various known ADK patterns."""
    # Pattern 1: .tools property
    if hasattr(toolset, 'tools'):
        res = toolset.tools
        return res() if callable(res) else res
    
    # Pattern 2: .get_tools() method
    if hasattr(toolset, 'get_tools'):
        return await toolset.get_tools()
    
    # Pattern 3: .list_mcp_tools()
    if hasattr(toolset, 'list_mcp_tools'):
        return await toolset.list_mcp_tools()

    raise AttributeError("Could not find a method to list tools on McpToolset.")

async def test_toolsets_v0():
    print("🚀 Starting MCP Connection Tests...\n")

    # --- Test Maps MCP ---
    print("--- Testing Maps MCP ---")
    try:
        maps_toolset = get_maps_mcp_toolset()
        # list_tools() is a standard method in the McpToolset
        tools = await get_tools_safely(maps_toolset)
        print(f"✅ Connection Successful. Found {len(tools)} tools.")
        print(f"🛠️ Sample Tool: {tools[0].name if tools else 'None'}")
    except Exception as e:
        print(f"❌ Maps MCP Failed: {e}")

    print("\n" + "-"*30 + "\n")

    # --- Test BigQuery MCP ---
    print("--- Testing BigQuery MCP ---")
    try:
        bq_toolset = get_bigquery_mcp_toolset()
        tools = await get_tools_safely(bq_toolset)
        print(f"✅ Connection Successful. Found {len(tools)} tools.")
        print(f"🛠️ Sample Tool: {tools[0].name if tools else 'None'}")
        
        # Optional: Deep test - Try to list datasets to verify permissions
        # We find the specific tool in the toolset to call it
        print("🔍 Attempting to list datasets (Deep Test)...")
        # Note: Tool names might vary slightly based on server version
        # We'll look for a tool that lists datasets
        # 
        if tools:
            for t in tools:
                print(f"Tool: {t.name}")
        else:
            print("⚠️ No tools found to verify permissions.") 

        # list_tool = next((t for t in tools if "list_datasets" in t.name), None)
        
        # if list_tool:
        #     # We assume the tool might take a project_id or use default
        #     # Check the tool schema if this fails
        #     result = await bq_toolset.call_tool(list_tool.name, arguments={})
        #     print("✅ BigQuery Data Access Verified.")
        # else:
        #     print("⚠️ Could not find 'list_datasets' tool to verify permissions.")

    except Exception as e:
        print(f"❌ BigQuery MCP Failed: {e}")
        print("💡 Tip: Ensure you ran 'gcloud auth application-default login'")

async def test_toolsets():
    print("🚀 Starting MCP Connection Tests...\n")

    # We put toolsets in a list to ensure we can close them all at the end
    active_toolsets = []

    try:
        # --- Test Maps ---
        maps_toolset = get_maps_mcp_toolset()
        active_toolsets.append(maps_toolset)
        
        # --- Test BigQuery ---
        bq_toolset = get_bigquery_mcp_toolset()
        active_toolsets.append(bq_toolset)

        # Logic to test tools goes here...
        # (Using your get_tools_safely logic)
        for ts in active_toolsets:
            tools = await get_tools_safely(ts)
            for t in tools:
                print(f"Tool: {t.name}")
            print(f"✅ Connection verified for {ts.__class__.__name__}")

    finally:
        print("\n🧹 Cleaning up connections...")
        for ts in active_toolsets:
            # Look for a close method to shut down background tasks gracefully
            if hasattr(ts, 'close'):
                await ts.close()
            # If the toolset uses a session manager internally:
            elif hasattr(ts, 'session_manager') and hasattr(ts.session_manager, 'close'):
                await ts.session_manager.close()
        
        # A tiny sleep gives the background tasks one last loop to finish exiting
        await asyncio.sleep(0.5)
        print("✨ Shutdown complete.")

if __name__ == "__main__":
    try:
        asyncio.run(test_toolsets())
    except KeyboardInterrupt:
        pass
