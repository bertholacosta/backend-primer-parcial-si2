"""Script de migración: agrega columna informacion_valida a la tabla AnalisisIA."""
from src.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    conn.execute(text('ALTER TABLE "AnalisisIA" ADD COLUMN IF NOT EXISTS informacion_valida BOOLEAN DEFAULT TRUE'))
    conn.commit()
    print("OK: Columna 'informacion_valida' agregada a la tabla AnalisisIA")
