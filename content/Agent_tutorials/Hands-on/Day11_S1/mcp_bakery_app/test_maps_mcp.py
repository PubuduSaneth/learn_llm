import asyncio
from tools import get_maps_mcp_toolset

async def list_available_tools():
    toolset = get_maps_mcp_toolset()
    MAPS_MCP_URL     = "https://mapstools.googleapis.com/mcp"
    
    print(f"Connecting to {MAPS_MCP_URL}...")
    try:
        # In ADK, get_tools() triggers the discovery process
        tools = await toolset.get_tools()
        
        print(f"\n✅ Connected! Found {len(tools)} tools available:\n")
        print(f"{'Tool Name':<30} | {'Description'}")
        print("-" * 80)
        
        for tool in tools:
            # ADK tools have 'name' and 'description' attributes
            print(f"{tool.name:<30} | {tool.description[:75]}...")
            
    except Exception as e:
        print(f"❌ Failed to list tools: {e}")
        print("\nPossible causes:")
        print("1. 'Google Maps Platform MCP' API is not enabled in Cloud Console.")
        print("2. Your API Key restriction doesn't include 'Google Maps Platform MCP'.")
        print("3. Networking/Firewall issue reaching mapstools.googleapis.com.")

if __name__ == "__main__":
    asyncio.run(list_available_tools())