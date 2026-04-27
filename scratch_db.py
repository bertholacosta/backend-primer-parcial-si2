import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    from src.database import SQLALCHEMY_DATABASE_URL
    DATABASE_URL = SQLALCHEMY_DATABASE_URL

print(f"Connecting to {DATABASE_URL}...")
engine = create_engine(DATABASE_URL)

try:
    with engine.connect() as conn:
        print("Adding estado to Mecanico...")
        conn.execute(text('ALTER TABLE "Mecanico" ADD COLUMN IF NOT EXISTS estado VARCHAR(50) DEFAULT \'Disponible\';'))
        
        print("Creating IncidenteMecanico...")
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS "IncidenteMecanico" (
                incidente_id INTEGER NOT NULL,
                mecanico_id INTEGER NOT NULL,
                PRIMARY KEY (incidente_id, mecanico_id),
                FOREIGN KEY(incidente_id) REFERENCES "Incidente" (id) ON DELETE CASCADE,
                FOREIGN KEY(mecanico_id) REFERENCES "Mecanico" (id) ON DELETE CASCADE
            );
        '''))
        conn.commit()
        print("Done!")
except Exception as e:
    print(f"Error: {e}")
