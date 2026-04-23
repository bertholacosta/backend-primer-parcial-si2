from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from .. import models, schemas
from ..deps import get_current_user
from ..bitacora_util import registrar_bitacora

router = APIRouter(
    prefix="/roles",
    tags=["Roles y Permisos"]
)

# --- Endpoints Principales de Roles ---

@router.get("/", response_model=List[schemas.Rol])
def get_roles(db: Session = Depends(get_db)):
    """Extrae todos los roles junto con sus permisos asignados."""
    roles = db.query(models.Rol).all()
    return roles

@router.post("/", response_model=schemas.Rol, status_code=status.HTTP_201_CREATED)
def create_role(request: Request, role_data: schemas.RolCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    """Crea un nuevo Rol sin permisos iniciales."""
    # Check si existe por nombre
    if db.query(models.Rol).filter(models.Rol.Nombre == role_data.Nombre).first():
        raise HTTPException(status_code=400, detail="Ya existe un rol con ese nombre")
        
    nuevo_rol = models.Rol(Nombre=role_data.Nombre)
    db.add(nuevo_rol)
    db.commit()
    db.refresh(nuevo_rol)

    registrar_bitacora(
        db, current_user.Id, "Crear Rol",
        f"Creó el rol '{nuevo_rol.Nombre}'",
        ip=request.client.host if request.client else "0.0.0.0"
    )
    return nuevo_rol

@router.put("/{role_id}", response_model=schemas.Rol)
def update_role(request: Request, role_id: int, role_data: schemas.RolCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    """Permite cambiar el nombre de un Rol."""
    db_rol = db.query(models.Rol).filter(models.Rol.Id == role_id).first()
    if not db_rol:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
        
    if role_data.Nombre != db_rol.Nombre:
        if db.query(models.Rol).filter(models.Rol.Nombre == role_data.Nombre).first():
            raise HTTPException(status_code=400, detail="Ya existe un rol con ese nombre")
        db_rol.Nombre = role_data.Nombre
        db.commit()
        db.refresh(db_rol)
        
    registrar_bitacora(
        db, current_user.Id, "Editar Rol",
        f"Editó el rol #{role_id} a '{db_rol.Nombre}'",
        ip=request.client.host if request.client else "0.0.0.0"
    )
    return db_rol

@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(request: Request, role_id: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    """Elimina el Rol, con protección de integridad si está en uso."""
    db_rol = db.query(models.Rol).filter(models.Rol.Id == role_id).first()
    if not db_rol:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
        
    # Verificar Integridad y Uso:
    usuarios_activos = db.query(models.Usuario).filter(models.Usuario.IdRol == role_id).count()
    if usuarios_activos > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Imposible eliminar. El rol está actualmente asignado a {usuarios_activos} usuario(s)."
        )
        
    # Limpiamos permisos asignados en tabla intermedia a través de la relación de SQLAlchemy (se borran automágicamente por UnitOfWork en muchos a muchos, o podemos simplemente limpiarlo):
    nombre_eliminado = db_rol.Nombre
    db_rol.permisos.clear()
    
    db.delete(db_rol)
    db.commit()

    registrar_bitacora(
        db, current_user.Id, "Eliminar Rol",
        f"Eliminó el rol '{nombre_eliminado}'",
        ip=request.client.host if request.client else "0.0.0.0"
    )
    return None

# --- Endpoints de Permisos ---

@router.get("/permisos/todos", response_model=List[schemas.Permiso])
def get_all_permisos(db: Session = Depends(get_db)):
    """Extrae la lista maestra de todos los permisos disponibles en el sistema."""
    return db.query(models.Permiso).all()

@router.post("/{role_id}/permisos/{permiso_id}", status_code=status.HTTP_201_CREATED)
def assign_permiso_to_role(request: Request, role_id: int, permiso_id: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    """Asigna un Permiso específico a un Rol."""
    db_rol = db.query(models.Rol).filter(models.Rol.Id == role_id).first()
    if not db_rol:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
        
    db_perm = db.query(models.Permiso).filter(models.Permiso.Id == permiso_id).first()
    if not db_perm:
        raise HTTPException(status_code=404, detail="Permiso no encontrado")
        
    # Assign if not already assigned
    if db_perm not in db_rol.permisos:
        db_rol.permisos.append(db_perm)
        db.commit()

    registrar_bitacora(
        db, current_user.Id, "Asignar Permiso",
        f"Asignó permiso '{db_perm.Nombre}' al rol '{db_rol.Nombre}'",
        ip=request.client.host if request.client else "0.0.0.0"
    )
    return {"message": "Permiso asignado"}

@router.delete("/{role_id}/permisos/{permiso_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_permiso_from_role(request: Request, role_id: int, permiso_id: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    """Revoca un Permiso de un Rol."""
    db_rol = db.query(models.Rol).filter(models.Rol.Id == role_id).first()
    if not db_rol:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
        
    db_perm = db.query(models.Permiso).filter(models.Permiso.Id == permiso_id).first()
    if not db_perm:
        raise HTTPException(status_code=404, detail="Permiso no encontrado")
        
    if db_perm in db_rol.permisos:
        db_rol.permisos.remove(db_perm)
        db.commit()

    registrar_bitacora(
        db, current_user.Id, "Revocar Permiso",
        f"Revocó permiso '{db_perm.Nombre}' del rol '{db_rol.Nombre}'",
        ip=request.client.host if request.client else "0.0.0.0"
    )
    return None
