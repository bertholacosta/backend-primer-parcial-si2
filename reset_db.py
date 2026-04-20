from src.database import engine, Base
from sqlalchemy import text

print("Limpiando la base de datos PostgreSQL completa (CASCADE)...")
try:
    with engine.connect() as conn:
        # Destruye el schema público entero y lo vuelve a crear para eliminar TODAS las tablas y sus dependencias sin importar el orden viejo.
        conn.execute(text("DROP SCHEMA public CASCADE;"))
        conn.execute(text("CREATE SCHEMA public;"))
        conn.execute(text("GRANT ALL ON SCHEMA public TO public;"))
        conn.commit()
    print("Schema limpiado.")
except Exception as e:
    print(f"Error al limpiar schema (¿quizás no es Postgres?): {e}")

print("Creando todas las tablas nuevas con el esquema actualizado...")
Base.metadata.create_all(bind=engine)

print("¡Base de datos reseteada con éxito!")
