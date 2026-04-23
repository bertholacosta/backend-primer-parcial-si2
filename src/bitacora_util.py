from datetime import date
from sqlalchemy.orm import Session
from . import models


def registrar_bitacora(
    db: Session,
    usuario_id: int,
    accion: str,
    descripcion: str,
    ip: str = "0.0.0.0"
):
    """Registra una entrada en la bitácora de actividades del sistema."""
    entrada = models.Bitacora(
        accion=accion,
        descripcion=descripcion,
        fecha=date.today(),
        ip=ip,
        usuario_id=usuario_id
    )
    db.add(entrada)
    db.commit()
