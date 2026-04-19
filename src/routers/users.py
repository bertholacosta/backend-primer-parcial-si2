from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from .. import models, schemas
from ..security import get_password_hash

router = APIRouter(
    prefix="/users",
    tags=["Usuarios"]
)

@router.get("/", response_model=List[schemas.Usuario])
def get_users(db: Session = Depends(get_db), skip: int = 0, limit: int = 100):
    users = db.query(models.Usuario).offset(skip).limit(limit).all()
    return users

@router.get("/roles", response_model=List[schemas.Rol])
def get_roles(db: Session = Depends(get_db)):
    roles = db.query(models.Rol).all()
    return roles

@router.put("/{user_id}", response_model=schemas.Usuario)
def update_user(user_id: int, user_data: schemas.UsuarioUpdate, db: Session = Depends(get_db)):
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
        db_user.IdRol = user_data.IdRol
        
    db.commit()
    db.refresh(db_user)
    return db_user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.Usuario).filter(models.Usuario.Id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Optional: Delete related records in dependent tables first
    # e.g., db.query(models.Administrador).filter(models.Administrador.IdUsuario == user_id).delete()
    # e.g., db.query(models.Conductor).filter(models.Conductor.IdUsuario == user_id).delete()
    # e.g., db.query(models.Taller).filter(models.Taller.IdUsuario == user_id).delete()
    # Due to SQLAlchemy relationship cascades not being strictly set up for deletes, we might need manual deletes.
    
    # Manually deleting profile links to prevent constraint violations
    db.query(models.Administrador).filter(models.Administrador.IdUsuario == user_id).delete()
    db.query(models.Conductor).filter(models.Conductor.IdUsuario == user_id).delete()
    db.query(models.Taller).filter(models.Taller.IdUsuario == user_id).delete()
    db.query(models.Vehiculo).filter(models.Vehiculo.IdUsuario == user_id).delete()

    db.delete(user)
    db.commit()
    return None
