from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.database import get_db
from src import models
from src import ai_service

router = APIRouter(
    prefix="/ia",
    tags=["Inteligencia Artificial"]
)

@router.post("/analizar-evidencia/{incidente_id}")
def analizar_evidencia_endpoint(incidente_id: int, db: Session = Depends(get_db)):
    # Buscar el incidente y su evidencia
    incidente = db.query(models.Incidente).filter(models.Incidente.id == incidente_id).first()
    if not incidente:
        raise HTTPException(status_code=404, detail="Incidente no encontrado")
        
    evidencia = db.query(models.Evidencia).filter(models.Evidencia.incidente_id == incidente_id).first()
    if not evidencia:
        raise HTTPException(status_code=404, detail="No hay evidencia asociada a este incidente")
        
    # En un caso real, pasaríamos evidencia.fotos a Gemini si fueran URLs públicas.
    # Por ahora pasaremos la descripción.
    descripcion_usuario = evidencia.descripcion or "El usuario no proporcionó descripción textual."
    
    # Llamar a Gemini
    analisis = ai_service.analizar_evidencia_visual(descripcion=descripcion_usuario)
    
    return {
        "incidente_id": incidente_id,
        "analisis_ia": analisis
    }

@router.post("/generar-reporte/{incidente_id}")
def generar_reporte_endpoint(incidente_id: int, db: Session = Depends(get_db)):
    incidente = db.query(models.Incidente).filter(models.Incidente.id == incidente_id).first()
    if not incidente:
        raise HTTPException(status_code=404, detail="Incidente no encontrado")
        
    datos_dict = {
        "id": incidente.id,
        "estado": incidente.estado,
        "fecha": incidente.fecha,
        "taller_id": incidente.taller_id,
        "coordenadagps": incidente.coordenadagps
    }
    
    reporte = ai_service.generar_reporte_enriquecido(datos_dict)
    
    return {
        "incidente_id": incidente_id,
        "reporte_ejecutivo": reporte
    }

import os
import joblib
from pydantic import BaseModel

class DatosGravedad(BaseModel):
    tipo_averia: str
    clima: str
    distancia_km: float

@router.post("/clasificar-gravedad")
def clasificar_gravedad_endpoint(datos: DatosGravedad):
    base_dir = os.path.dirname(__file__)
    model_path = os.path.join(base_dir, '..', 'ml_models', 'modelo_gravedad.joblib')
    encoders_path = os.path.join(base_dir, '..', 'ml_models', 'encoders.joblib')
    
    if not os.path.exists(model_path) or not os.path.exists(encoders_path):
        raise HTTPException(status_code=500, detail="Modelo predictivo no entrenado. Ejecuta train_model.py")
        
    try:
        clf = joblib.load(model_path)
        encoders = joblib.load(encoders_path)
        
        le_averia = encoders['averia']
        le_clima = encoders['clima']
        
        # Manejar posibles valores desconocidos (esto es una demo)
        averia_enc = le_averia.transform([datos.tipo_averia])[0] if datos.tipo_averia in le_averia.classes_ else 0
        clima_enc = le_clima.transform([datos.clima])[0] if datos.clima in le_clima.classes_ else 0
        
        X_pred = [[averia_enc, clima_enc, datos.distancia_km]]
        prediccion = clf.predict(X_pred)
        
        return {
            "datos_recibidos": datos.dict(),
            "prediccion_gravedad": prediccion[0]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en predicción ML: {str(e)}")

