from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from .database import engine, Base, get_db
from . import models

# Crear todas las tablas en la base de datos
Base.metadata.create_all(bind=engine)

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Backend API - Primer Parcial SI2",
    description="API con Sistema de Login usando JWT y Base de Datos PostgreSQL",
    version="1.0.0"
)

# Habilitar CORS para permitir llamadas estáticas o locales desde Angular
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from src.routers import auth, users, roles, mecanicos

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(roles.router)
app.include_router(mecanicos.router)

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
