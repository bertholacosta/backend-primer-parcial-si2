from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import datetime

from ..database import get_db
from .. import models, schemas
from ..deps import get_current_user

router = APIRouter(
    prefix="/incidentes",
    tags=["Incidentes y Emergencias"]
)

@router.post("/reportar", response_model=schemas.Incidente)
def reportar_incidente(
    payload: schemas.IncidenteCreate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    if not current_user.conductor:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo conductores pueden reportar siniestros")

    # Verificar que el conductor sí tiene registrado ese vehículo (y tomar el VehiculoConductor)
    vehiculo_conductor = db.query(models.VehiculoConductor).filter(
        models.VehiculoConductor.conductor_id == current_user.conductor.IdUsuario,
        models.VehiculoConductor.vehiculo_id == payload.vehiculo_id
    ).first()

    if not vehiculo_conductor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="No tienes registrado este vehículo para reportarlo en un siniestro"
        )

    # Crear Incidente
    fecha_actual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    nuevo_incidente = models.Incidente(
        coordenadagps=payload.coordenadagps,
        estado=payload.estado or "Reportado",
        fecha=payload.fecha or fecha_actual,
        vehiculoconductor_id=vehiculo_conductor.id
    )

    db.add(nuevo_incidente)
    db.commit()
    db.refresh(nuevo_incidente)

    # Crear Evidencia ligada al Incidente
    evidencia_data = payload.evidencia.model_dump() if hasattr(payload.evidencia, 'model_dump') else payload.evidencia.dict()
    nueva_evidencia = models.Evidencia(
        audio=evidencia_data.get('audio'),
        descripcion=evidencia_data.get('descripcion'),
        fotos=evidencia_data.get('fotos'),
        incidente_id=nuevo_incidente.id
    )
    
    db.add(nueva_evidencia)
    db.commit()
    db.refresh(nuevo_incidente) # Refrescar para traernos la evidencia inyectada en ORM

    return nuevo_incidente
