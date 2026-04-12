from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from .database import engine, Base, get_db

# Crear todas las tablas en la base de datos
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Backend API - Primer Parcial SI2",
    description="API inicial generada con FastAPI y PostgreSQL",
    version="1.0.0"
)

@app.get("/")
def read_root():
    return {"message": "Bienvenido a la API del proyecto de Backend"}

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    # Ejecuta un query simple para confirmar que hay conexión a la base de datos
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return {"status": "error", "database": "disconnected", "details": str(e)}
