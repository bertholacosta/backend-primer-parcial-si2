from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from .database import engine, Base, get_db
from . import models
import os

# Crear todas las tablas en la base de datos
Base.metadata.create_all(bind=engine)

from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

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

from src.routers import auth, users, roles, mecanicos, vehiculos, incidentes, bitacora, notificaciones, profile, ia

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(roles.router)
app.include_router(mecanicos.router)
app.include_router(vehiculos.router)
app.include_router(incidentes.router)
app.include_router(bitacora.router)
app.include_router(notificaciones.router)
app.include_router(profile.router)
app.include_router(ia.router)

# Servir archivos estáticos (fotos de incidentes)
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

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
