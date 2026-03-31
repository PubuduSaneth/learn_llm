import os
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("MAPS_API_KEY")

if not key:
    print("❌ Error: MAPS_API_KEY is not set in .env")
elif key == "no_api_key_found":
    print("❌ Error: The script is using the fallback 'no_api_key_found' string.")
else:
    print(f"✅ Key loaded (starts with: {key[:5]}...)")

maps_api_key = os.getenv("MAPS_API_KEY")
if not maps_api_key:
    raise EnvironmentError(
        "MAPS_API_KEY is not set. Add it to your .env file before starting the agent."
    )
else:
    print(f"✅ MAPS_API_KEY is set (starts with: {maps_api_key[:5]}...)")