from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, schemas
from ..security import get_password_hash
from ..deps import get_current_user
from ..bitacora_util import registrar_bitacora

router = APIRouter(
    prefix="/profile",
    tags=["Perfil de Usuario"]
)


@router.get("/me", response_model=schemas.ProfileOut)
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    """Devuelve el perfil completo del usuario autenticado, incluyendo datos según su rol."""
    rol_nombre = current_user.rol.Nombre if current_user.rol else None

    admin_data = None
    taller_data = None
    conductor_data = None

    if current_user.administrador:
        admin_data = schemas.AdminProfileData(
            Usuario=current_user.administrador.Usuario
        )

    if current_user.talleres and len(current_user.talleres) > 0:
        t = current_user.talleres[0]  # Un usuario taller tiene un solo taller
        taller_data = schemas.TallerProfileData(
            Id=t.Id,
            Nombre=t.Nombre,
            Direccion=t.Direccion,
            Coordenadas=t.Coordenadas,
            Cap=t.Cap,
            Capmax=t.Capmax
        )

    if current_user.conductor:
        conductor_data = schemas.ConductorProfileData(
            CI=current_user.conductor.CI,
            Nombre=current_user.conductor.Nombre,
            Apellidos=current_user.conductor.Apellidos,
            Fechanac=current_user.conductor.Fechanac
        )

    return schemas.ProfileOut(
        Id=current_user.Id,
        Correo=current_user.Correo,
        rol_nombre=rol_nombre,
        administrador=admin_data,
        taller=taller_data,
        conductor=conductor_data
    )


@router.put("/me", response_model=schemas.ProfileOut)
def update_my_profile(
    request: Request,
    profile_data: schemas.ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    """Actualiza el perfil del usuario autenticado."""
    # Actualizar correo
    if profile_data.Correo and profile_data.Correo != current_user.Correo:
        existing = db.query(models.Usuario).filter(
            models.Usuario.Correo == profile_data.Correo,
            models.Usuario.Id != current_user.Id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Este correo ya está en uso por otro usuario")
        current_user.Correo = profile_data.Correo

    # Actualizar contraseña
    if profile_data.Password:
        current_user.Password = get_password_hash(profile_data.Password)

    # Actualizar datos de Administrador
    if current_user.administrador and profile_data.admin_usuario is not None:
        current_user.administrador.Usuario = profile_data.admin_usuario

    # Actualizar datos de Taller
    if current_user.talleres and len(current_user.talleres) > 0:
        t = current_user.talleres[0]
        if profile_data.taller_nombre is not None:
            t.Nombre = profile_data.taller_nombre
        if profile_data.taller_direccion is not None:
            t.Direccion = profile_data.taller_direccion
        if profile_data.taller_coordenadas is not None:
            t.Coordenadas = profile_data.taller_coordenadas
        if profile_data.taller_cap is not None:
            t.Cap = profile_data.taller_cap
        if profile_data.taller_capmax is not None:
            t.Capmax = profile_data.taller_capmax

    # Actualizar datos de Conductor
    if current_user.conductor:
        if profile_data.conductor_ci is not None:
            current_user.conductor.CI = profile_data.conductor_ci
        if profile_data.conductor_nombre is not None:
            current_user.conductor.Nombre = profile_data.conductor_nombre
        if profile_data.conductor_apellidos is not None:
            current_user.conductor.Apellidos = profile_data.conductor_apellidos
        if profile_data.conductor_fechanac is not None:
            current_user.conductor.Fechanac = profile_data.conductor_fechanac

    db.commit()
    db.refresh(current_user)

    registrar_bitacora(
        db, current_user.Id, "Editar Perfil",
        f"El usuario {current_user.Correo} actualizó su perfil",
        ip=request.client.host if request.client else "0.0.0.0"
    )

    # Re-construir la respuesta
    return get_my_profile(db=db, current_user=current_user)


@router.put("/me/ubicacion", response_model=schemas.ProfileOut)
def update_ubicacion_taller(
    request: Request,
    ubicacion: schemas.UbicacionUpdate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    """Actualiza la ubicación georreferenciada del taller (solo para usuarios con rol Taller)."""
    if not current_user.talleres or len(current_user.talleres) == 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo usuarios con perfil de Taller pueden actualizar la ubicación"
        )

    taller = current_user.talleres[0]
    taller.Coordenadas = ubicacion.Coordenadas
    if ubicacion.Direccion is not None:
        taller.Direccion = ubicacion.Direccion

    db.commit()
    db.refresh(current_user)

    registrar_bitacora(
        db, current_user.Id, "Actualizar Ubicación",
        f"El taller '{taller.Nombre}' actualizó su ubicación a {ubicacion.Coordenadas}",
        ip=request.client.host if request.client else "0.0.0.0"
    )

    return get_my_profile(db=db, current_user=current_user)
