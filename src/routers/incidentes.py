from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
import datetime
import math

from ..database import get_db
from .. import models, schemas
from ..deps import get_current_user

router = APIRouter(
    prefix="/incidentes",
    tags=["Incidentes y Emergencias"]
)


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calcula la distancia en km entre dos coordenadas GPS usando la fórmula de Haversine."""
    R = 6371  # Radio de la Tierra en km
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(d_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)


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


@router.get("/mis-incidentes", response_model=List[schemas.IncidenteDetalle])
def mis_incidentes(
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    """Devuelve todos los incidentes del conductor actual con evidencias y taller asignado."""
    if not current_user.conductor:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo conductores pueden ver sus incidentes")

    # Obtener todos los VehiculoConductor del conductor
    vc_ids = [vc.id for vc in current_user.conductor.vehiculo_conductores]

    if not vc_ids:
        return []

    incidentes = (
        db.query(models.Incidente)
        .options(joinedload(models.Incidente.evidencias), joinedload(models.Incidente.taller))
        .filter(models.Incidente.vehiculoconductor_id.in_(vc_ids))
        .order_by(models.Incidente.id.desc())
        .all()
    )

    return incidentes


@router.get("/talleres-disponibles", response_model=List[schemas.TallerDisponible])
def talleres_disponibles(
    lat: Optional[float] = Query(None, description="Latitud del conductor"),
    lng: Optional[float] = Query(None, description="Longitud del conductor"),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    """Lista talleres con capacidad disponible, ordenados por cercanía si se proveen coordenadas."""
    # Obtener talleres con capacidad disponible (Cap < Capmax)
    talleres = db.query(models.Taller).all()

    resultado = []
    for t in talleres:
        cap = t.Cap or 0
        capmax = t.Capmax or 0
        # Solo incluir talleres que tengan capacidad (o si no tienen límite definido)
        if capmax > 0 and cap >= capmax:
            continue

        distancia = None
        if lat is not None and lng is not None and t.Coordenadas:
            try:
                parts = t.Coordenadas.replace(" ", "").split(",")
                t_lat = float(parts[0])
                t_lng = float(parts[1])
                distancia = _haversine(lat, lng, t_lat, t_lng)
            except (ValueError, IndexError):
                distancia = None

        resultado.append(schemas.TallerDisponible(
            Id=t.Id,
            Nombre=t.Nombre,
            Direccion=t.Direccion,
            Coordenadas=t.Coordenadas,
            Cap=cap,
            Capmax=capmax,
            distancia_km=distancia
        ))

    # Ordenar por distancia (talleres sin distancia al final)
    resultado.sort(key=lambda x: x.distancia_km if x.distancia_km is not None else 99999)

    return resultado


@router.patch("/{incidente_id}/asignar-taller", response_model=schemas.IncidenteDetalle)
def asignar_taller(
    incidente_id: int,
    payload: schemas.AsignarTaller,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    """Permite al conductor seleccionar un taller para su incidente."""
    if not current_user.conductor:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo conductores pueden asignar talleres")

    # Verificar que el incidente pertenece al conductor
    vc_ids = [vc.id for vc in current_user.conductor.vehiculo_conductores]
    incidente = (
        db.query(models.Incidente)
        .options(joinedload(models.Incidente.evidencias), joinedload(models.Incidente.taller))
        .filter(models.Incidente.id == incidente_id, models.Incidente.vehiculoconductor_id.in_(vc_ids))
        .first()
    )

    if not incidente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incidente no encontrado o no te pertenece")

    # Verificar que el taller existe
    taller = db.query(models.Taller).filter(models.Taller.Id == payload.taller_id).first()
    if not taller:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Taller no encontrado")

    # Asignar taller y cambiar estado
    incidente.taller_id = payload.taller_id
    incidente.estado = "Asignado"

    # Incrementar la capacidad usada del taller
    if taller.Cap is not None:
        taller.Cap = (taller.Cap or 0) + 1

    db.commit()
    db.refresh(incidente)

    return incidente
