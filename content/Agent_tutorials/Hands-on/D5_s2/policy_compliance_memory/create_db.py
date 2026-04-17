from sqlalchemy import create_engine, text

# 1. Define your URL
db_url = "sqlite:///agent_history.db"

# 2. Create the engine
# This object manages the 'pool' of connections to the file
engine = create_engine(db_url, echo=True)

# 3. Open a connection once to force SQLite file creation.
with engine.connect() as conn:
	conn.execute(text("SELECT 1"))

# Note: 'echo=True' will log every SQL command to your console.
# Great for seeing exactly how the Agent saves your session!
