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
    role_name = user.rol.Nombre if user.rol else None
    permisos_list = [p.Nombre for p in user.rol.permisos] if user.rol and user.rol.permisos else []
    return {
        "access_token": access_token, 
        "token_type": "bearer", 
        "role": role_name,
        "permisos": permisos_list
    }

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

@router.post("/registrar-conductor", response_model=dict)
def register_conductor(conductor_data: schemas.ConductorRegistro, db: Session = Depends(get_db)):
    # Buscar si existe el rol Conductor, de lo contrario crearlo
    rol = db.query(models.Rol).filter(models.Rol.Nombre == "Conductor").first()
    if not rol:
        rol = models.Rol(Nombre="Conductor")
        db.add(rol)
        db.commit()
        db.refresh(rol)

    # Validar correo existente en Usuario
    if db.query(models.Usuario).filter(models.Usuario.Correo == conductor_data.Correo).first():
        raise HTTPException(status_code=400, detail="Este correo ya está registrado en el sistema")

    # Crear Usuario en DB
    hashed_pass = get_password_hash(conductor_data.Password)
    new_user = models.Usuario(Correo=conductor_data.Correo, Password=hashed_pass, IdRol=rol.Id)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Crear el Perfil del Conductor en DB y enlazar a Usuario
    nuevo_conductor = models.Conductor(
        IdUsuario=new_user.Id,
        CI=conductor_data.CI,
        Nombre=conductor_data.Nombre,
        Apellidos=conductor_data.Apellidos,
        Fechanac=conductor_data.Fechanac
    )
    db.add(nuevo_conductor)
    db.commit()
    return {"message": "Conductor registrado exitosamente"}

@router.post("/registrar-taller", response_model=dict)
def register_taller(taller_data: schemas.TallerRegistro, db: Session = Depends(get_db)):
    # Buscar si existe el rol Taller, de lo contrario crearlo
    rol = db.query(models.Rol).filter(models.Rol.Nombre == "Taller").first()
    if not rol:
        rol = models.Rol(Nombre="Taller")
        # Asegurarnos de que el nuevo rol Taller nazca con permiso de Gestionar Mecanicos si existe
        permiso = db.query(models.Permiso).filter(models.Permiso.Nombre == "Gestionar Mecanicos").first()
        if permiso:
            rol.permisos.append(permiso)
        db.add(rol)
        db.commit()
        db.refresh(rol)

    # Validar correo existente en Usuario
    if db.query(models.Usuario).filter(models.Usuario.Correo == taller_data.Correo).first():
        raise HTTPException(status_code=400, detail="Este correo ya está registrado por otra cuenta")

    # Crear Usuario en DB
    hashed_pass = get_password_hash(taller_data.Password)
    new_user = models.Usuario(Correo=taller_data.Correo, Password=hashed_pass, IdRol=rol.Id)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Crear Perfil de Taller
    nuevo_taller = models.Taller(
        IdUsuario=new_user.Id,
        Nombre=taller_data.Nombre,
        Direccion=taller_data.Direccion,
        Coordenadas=taller_data.Coordenadas,
        Cap=taller_data.Cap if taller_data.Cap is not None else 0,
        Capmax=taller_data.Capmax if taller_data.Capmax is not None else 10
    )
    db.add(nuevo_taller)
    db.commit()
    
    return {"message": "Taller registrado exitosamente. Ahora puede iniciar sesión."}
