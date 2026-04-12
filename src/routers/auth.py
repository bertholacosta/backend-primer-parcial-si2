from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import Annotated

from ..database import get_db
from .. import models, schemas
from ..security import verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, get_password_hash

# El Router para gestionar los endpoints
router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

# Establece de qué endpoint el Swagger UI debería extraer el token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

@router.post("/login", response_model=schemas.Token)
def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: Session = Depends(get_db)):
    # OAuth2PasswordRequestForm usa 'username' y 'password' por defecto. Interpretamos username como correo.
    user = db.query(models.Usuario).filter(models.Usuario.Correo == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.Password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo electrónico o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Crear token válido
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.Correo}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# Ruta adicionada convenientemente para poder testear el login fácilmente
@router.post("/registrar", response_model=dict)
def register_user(usuario: schemas.UsuarioCreate, db: Session = Depends(get_db)):
    # Verificar si existe el rol con id proporcionado
    rol = db.query(models.Rol).filter(models.Rol.Id == usuario.IdRol).first()
    if not rol:
        # Crea y asigna un rol básico si el IdRol no existe (para facilitar la prueba)
        rol = models.Rol(Id=usuario.IdRol, Nombre="Rol Generado Auto")
        db.add(rol)
        db.commit()
    
    # Validar correo existente
    db_user = db.query(models.Usuario).filter(models.Usuario.Correo == usuario.Correo).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Este correo ya está registrado")
    
    # Cifrar contraseña y guardar
    hashed_password = get_password_hash(usuario.Password)
    new_user = models.Usuario(Correo=usuario.Correo, Password=hashed_password, IdRol=usuario.IdRol)
    
    db.add(new_user)
    db.commit()
    return {"message": "Usuario registrado exitosamente"}
