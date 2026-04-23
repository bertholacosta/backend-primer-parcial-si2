from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from .. import models, schemas
from ..security import get_password_hash
from ..deps import get_current_user
from ..bitacora_util import registrar_bitacora

router = APIRouter(
    prefix="/users",
    tags=["Usuarios"]
)

def require_admin(current_user: models.Usuario = Depends(get_current_user)):
    """Dependencia que verifica que el usuario actual sea Administrador."""
    if not current_user.rol or current_user.rol.Nombre != "Administrador":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado. Se requieren permisos de Administrador."
        )
    return current_user

@router.get("/", response_model=List[schemas.Usuario])
def get_users(
    db: Session = Depends(get_db), 
    current_user: models.Usuario = Depends(require_admin),
    skip: int = 0, 
    limit: int = 100
):
    users = db.query(models.Usuario).offset(skip).limit(limit).all()
    return users

@router.get("/roles", response_model=List[schemas.Rol])
def get_roles(
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_admin)
):
    roles = db.query(models.Rol).all()
    return roles

@router.post("/", response_model=schemas.Usuario, status_code=status.HTTP_201_CREATED)
def create_user(
    request: Request,
    user_data: schemas.UsuarioCreate, 
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_admin)
):
    """Crea un nuevo usuario (solo accesible por Administradores)."""
    # Validar correo único
    if db.query(models.Usuario).filter(models.Usuario.Correo == user_data.Correo).first():
        raise HTTPException(status_code=400, detail="Este correo ya está registrado")
    
    # Validar que el rol existe
    rol = db.query(models.Rol).filter(models.Rol.Id == user_data.IdRol).first()
    if not rol:
        raise HTTPException(status_code=400, detail="El rol especificado no existe")
    
    hashed_password = get_password_hash(user_data.Password)
    new_user = models.Usuario(
        Correo=user_data.Correo, 
        Password=hashed_password, 
        IdRol=user_data.IdRol
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    registrar_bitacora(
        db, current_user.Id, "Crear Usuario",
        f"Creó el usuario {new_user.Correo} con rol {rol.Nombre}",
        ip=request.client.host if request.client else "0.0.0.0"
    )
    return new_user

@router.put("/{user_id}", response_model=schemas.Usuario)
def update_user(
    request: Request,
    user_id: int, 
    user_data: schemas.UsuarioUpdate, 
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_admin)
):
    db_user = db.query(models.Usuario).filter(models.Usuario.Id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    if user_data.Correo and user_data.Correo != db_user.Correo:
        # Ver si otro lo tiene
        if db.query(models.Usuario).filter(models.Usuario.Correo == user_data.Correo).first():
            raise HTTPException(status_code=400, detail="El correo ya se encuentra en uso por otro usuario")
        db_user.Correo = user_data.Correo
        
    if user_data.Password:
        db_user.Password = get_password_hash(user_data.Password)
        
    if user_data.IdRol is not None:
        # Validar que el rol existe
        rol = db.query(models.Rol).filter(models.Rol.Id == user_data.IdRol).first()
        if not rol:
            raise HTTPException(status_code=400, detail="El rol especificado no existe")
        db_user.IdRol = user_data.IdRol
        
    db.commit()
    db.refresh(db_user)

    registrar_bitacora(
        db, current_user.Id, "Editar Usuario",
        f"Editó al usuario #{user_id} ({db_user.Correo})",
        ip=request.client.host if request.client else "0.0.0.0"
    )
    return db_user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    request: Request,
    user_id: int, 
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_admin)
):
    user = db.query(models.Usuario).filter(models.Usuario.Id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # No permitir que el admin se elimine a sí mismo
    if user.Id == current_user.Id:
        raise HTTPException(status_code=400, detail="No puedes eliminar tu propia cuenta de administrador")
    
    correo_eliminado = user.Correo

    # Manually deleting profile links to prevent constraint violations
    db.query(models.Administrador).filter(models.Administrador.IdUsuario == user_id).delete()
    db.query(models.Conductor).filter(models.Conductor.IdUsuario == user_id).delete()
    db.query(models.Taller).filter(models.Taller.IdUsuario == user_id).delete()

    db.delete(user)
    db.commit()

    registrar_bitacora(
        db, current_user.Id, "Eliminar Usuario",
        f"Eliminó al usuario #{user_id} ({correo_eliminado})",
        ip=request.client.host if request.client else "0.0.0.0"
    )
    return None
