import os
from sqlalchemy import create_engine, text

# Get DB URL from env or use the one from database.py
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("No DATABASE_URL found. Will try to use the one from database.py")
    from src.database import SQLALCHEMY_DATABASE_URL
    DATABASE_URL = SQLALCHEMY_DATABASE_URL

print(f"Connecting to {DATABASE_URL}...")
engine = create_engine(DATABASE_URL)

try:
    with engine.connect() as conn:
        print("Altering table Mecanico...")
        conn.execute(text('ALTER TABLE "Mecanico" ALTER COLUMN fechanac TYPE BIGINT;'))
        conn.commit()
        print("Done!")
except Exception as e:
    print(f"Error: {e}")
