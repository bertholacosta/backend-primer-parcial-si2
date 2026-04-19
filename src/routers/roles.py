from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from .. import models, schemas

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
def create_role(role_data: schemas.RolCreate, db: Session = Depends(get_db)):
    """Crea un nuevo Rol sin permisos iniciales."""
    # Check si existe por nombre
    if db.query(models.Rol).filter(models.Rol.Nombre == role_data.Nombre).first():
        raise HTTPException(status_code=400, detail="Ya existe un rol con ese nombre")
        
    nuevo_rol = models.Rol(Nombre=role_data.Nombre)
    db.add(nuevo_rol)
    db.commit()
    db.refresh(nuevo_rol)
    return nuevo_rol

@router.put("/{role_id}", response_model=schemas.Rol)
def update_role(role_id: int, role_data: schemas.RolCreate, db: Session = Depends(get_db)):
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
        
    return db_rol

@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(role_id: int, db: Session = Depends(get_db)):
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
    db_rol.permisos.clear()
    
    db.delete(db_rol)
    db.commit()
    return None

# --- Endpoints de Permisos ---

@router.get("/permisos/todos", response_model=List[schemas.Permiso])
def get_all_permisos(db: Session = Depends(get_db)):
    """Extrae la lista maestra de todos los permisos disponibles en el sistema."""
    return db.query(models.Permiso).all()

@router.post("/{role_id}/permisos/{permiso_id}", status_code=status.HTTP_201_CREATED)
def assign_permiso_to_role(role_id: int, permiso_id: int, db: Session = Depends(get_db)):
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
        
    return {"message": "Permiso asignado"}

@router.delete("/{role_id}/permisos/{permiso_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_permiso_from_role(role_id: int, permiso_id: int, db: Session = Depends(get_db)):
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
        
    return None
