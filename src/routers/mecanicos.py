from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from .. import models, schemas
from ..security import get_password_hash
from ..deps import get_current_user
from ..bitacora_util import registrar_bitacora

router = APIRouter(
    prefix="/mecanicos",
    tags=["Mecanicos"]
)

@router.get("/", response_model=List[schemas.MecanicoOut])
def get_mecanicos_by_taller(db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    """Obtiene todos los mecanicos que pertenecen al taller del usuario actual (si es un taller)."""
    # Verificar si el current_user tiene un Taller asignado
    taller = db.query(models.Taller).filter(models.Taller.IdUsuario == current_user.Id).first()
    
    if taller:
        # Es un taller, devolver solo sus mecanicos
        mecanicos = db.query(models.Mecanico).filter(models.Mecanico.taller_id == taller.Id).all()
        return mecanicos
    elif current_user.rol and current_user.rol.Nombre == 'Administrador':
        # Es un admin root, devolver todos (opcional)
        return db.query(models.Mecanico).all()
    else:
        raise HTTPException(status_code=403, detail="No autorizado para visualizar mecánicos")

@router.post("/", response_model=schemas.MecanicoOut, status_code=status.HTTP_201_CREATED)
def create_mecanico(request: Request, mecanico_data: schemas.MecanicoRegistro, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    """Registra y asigna un mecánico al Taller que ejecuta la petición."""
    taller = db.query(models.Taller).filter(models.Taller.IdUsuario == current_user.Id).first()
    if not taller:
        raise HTTPException(status_code=403, detail="Debe ser un Taller registrado para crear mecánicos")

    # Verificar si el correo ya existe
    if db.query(models.Usuario).filter(models.Usuario.Correo == mecanico_data.correo).first():
        raise HTTPException(status_code=400, detail="Este correo ya está registrado en el sistema")

    # Rol Mecanico 
    rol = db.query(models.Rol).filter(models.Rol.Nombre == 'Mecanico').first()
    if not rol:
        rol = models.Rol(Nombre='Mecanico')
        db.add(rol)
        db.commit()
        db.refresh(rol)

    # Crear Usuario
    hashed_pass = get_password_hash(mecanico_data.password)
    new_user = models.Usuario(Correo=mecanico_data.correo, Password=hashed_pass, IdRol=rol.Id)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Crear Perfil Mecanico
    nuevo_mecanico = models.Mecanico(
        id=new_user.Id,
        ci=mecanico_data.ci,
        extci=mecanico_data.extci,
        nombre=mecanico_data.nombre,
        apellidos=mecanico_data.apellidos,
        fechanac=mecanico_data.fechanac,
        taller_id=taller.Id
    )
    db.add(nuevo_mecanico)
    db.commit()
    db.refresh(nuevo_mecanico)

    registrar_bitacora(
        db, current_user.Id, "Crear Mecánico",
        f"Registró al mecánico {mecanico_data.nombre} {mecanico_data.apellidos}",
        ip=request.client.host if request.client else "0.0.0.0"
    )
    return nuevo_mecanico

@router.put("/{mecanico_id}", response_model=schemas.MecanicoOut)
def update_mecanico(request: Request, mecanico_id: int, m_update: schemas.MecanicoUpdate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    """Edita info de un mecanico (solo por admin o por el taller dueño)."""
    mecanico = db.query(models.Mecanico).filter(models.Mecanico.id == mecanico_id).first()
    if not mecanico:
        raise HTTPException(status_code=404, detail="Mecánico no encontrado")

    # Validar propiedad
    taller = db.query(models.Taller).filter(models.Taller.IdUsuario == current_user.Id).first()
    if not taller or mecanico.taller_id != taller.Id:
        if not (current_user.rol and current_user.rol.Nombre == 'Administrador'):
            raise HTTPException(status_code=403, detail="No puedes editar mecánicos de otros talleres")

    if m_update.nombre is not None:
        mecanico.nombre = m_update.nombre
    if m_update.apellidos is not None:
        mecanico.apellidos = m_update.apellidos
    if m_update.ci is not None:
        mecanico.ci = m_update.ci
    if m_update.extci is not None:
        mecanico.extci = m_update.extci
    if m_update.fechanac is not None:
        mecanico.fechanac = m_update.fechanac

    db.commit()
    db.refresh(mecanico)

    registrar_bitacora(
        db, current_user.Id, "Editar Mecánico",
        f"Editó al mecánico #{mecanico_id}",
        ip=request.client.host if request.client else "0.0.0.0"
    )
    return mecanico

@router.delete("/{mecanico_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_mecanico(request: Request, mecanico_id: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    """Da de baja a un mecánico eliminando su perfil y su usuario base."""
    mecanico = db.query(models.Mecanico).filter(models.Mecanico.id == mecanico_id).first()
    if not mecanico:
        raise HTTPException(status_code=404, detail="Mecánico no encontrado")

    taller = db.query(models.Taller).filter(models.Taller.IdUsuario == current_user.Id).first()
    if not taller or mecanico.taller_id != taller.Id:
        if not (current_user.rol and current_user.rol.Nombre == 'Administrador'):
            raise HTTPException(status_code=403, detail="No puedes dar de baja técnicos que no te pertenecen")

    # Capturar Id del usuario
    user_id = mecanico.id

    # ONDelete Cascade is built in DB, but sometimes SQLite needs manual trigger, so we delete both
    db.delete(mecanico)
    
    # Check if we should delete the base User account as well (Optional but highly recommended since he is being fired)
    base_user = db.query(models.Usuario).filter(models.Usuario.Id == user_id).first()
    if base_user:
        db.delete(base_user)

    db.commit()

    registrar_bitacora(
        db, current_user.Id, "Eliminar Mecánico",
        f"Dio de baja al mecánico #{mecanico_id}",
        ip=request.client.host if request.client else "0.0.0.0"
    )
    return None
