from google.adk.apps import App, EventsCompactionConfig
from google.adk.agents.context_cache_config import ContextCacheConfig
from agent import my_agent

# Configure the ADK Runtime
app = App(
    name='long-memory-agent',
    root_agent=my_agent,
    
    # 1. Context Caching: Handles the 'Static Instruction' (Policy Manual)
    context_cache_config=ContextCacheConfig(
        min_tokens=2048,    # Only trigger cache for large prompts
        ttl_seconds=1800,   # Keep the policy manual in cache for 30 mins
        cache_intervals=10  # Automatically refresh the cache after 10 turns
    ),

    # 2. Context Compression: Handles the 'Live History' (The Conversation)
    events_compaction_config=EventsCompactionConfig(
        compaction_interval=3, # Every 3 user turns, summarize the history
        overlap_size=1         # Keep the most recent turn in full to maintain flow
    )
)

if __name__ == "__main__":
    # Start the local ADK development server
    # Running this allows you to see the "Compaction Events" in the dev UI
    app.run()
