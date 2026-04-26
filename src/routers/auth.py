from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import Annotated

from ..database import get_db
from .. import models, schemas
from ..security import verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, get_password_hash
from ..bitacora_util import registrar_bitacora

# El Router para gestionar los endpoints
router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

# Establece de qué endpoint el Swagger UI debería extraer el token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

@router.post("/login", response_model=schemas.Token)
def login_for_access_token(request: Request, form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: Session = Depends(get_db)):
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
    # Registrar en bitácora
    registrar_bitacora(
        db, user.Id, "Inicio de Sesión",
        f"El usuario {user.Correo} inició sesión",
        ip=request.client.host if request.client else "0.0.0.0"
    )

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
def register_conductor(request: Request, conductor_data: schemas.ConductorRegistro, db: Session = Depends(get_db)):
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

    registrar_bitacora(
        db, new_user.Id, "Registro",
        f"Nuevo conductor registrado: {conductor_data.Nombre} {conductor_data.Apellidos}",
        ip=request.client.host if request.client else "0.0.0.0"
    )
    return {"message": "Conductor registrado exitosamente"}

@router.post("/registrar-taller", response_model=dict)
def register_taller(request: Request, taller_data: schemas.TallerRegistro, db: Session = Depends(get_db)):
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

    registrar_bitacora(
        db, new_user.Id, "Registro",
        f"Nuevo taller registrado: {taller_data.Nombre}",
        ip=request.client.host if request.client else "0.0.0.0"
    )
    
    return {"message": "Taller registrado exitosamente. Ahora puede iniciar sesión."}


# --- Recuperación de Contraseña ---

@router.post("/solicitar-reset", response_model=schemas.MensajeResponse)
def solicitar_reset_password(payload: schemas.PasswordResetRequest, db: Session = Depends(get_db)):
    """Envía un correo con un link para restablecer la contraseña."""
    user = db.query(models.Usuario).filter(models.Usuario.Correo == payload.correo).first()

    # Siempre retornar éxito para no revelar si el correo existe
    if not user:
        return {"message": "Si el correo está registrado, recibirás un enlace para restablecer tu contraseña."}

    # Crear token con expiración de 30 minutos
    reset_token = create_access_token(
        data={"sub": user.Correo, "type": "password_reset"},
        expires_delta=timedelta(minutes=30)
    )

    # Enviar email
    try:
        from ..email_util import enviar_email_reset
        enviar_email_reset(user.Correo, reset_token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al enviar el correo: {str(e)}"
        )

    return {"message": "Si el correo está registrado, recibirás un enlace para restablecer tu contraseña."}


@router.post("/restablecer-password", response_model=schemas.MensajeResponse)
def restablecer_password(payload: schemas.PasswordReset, db: Session = Depends(get_db)):
    """Restablece la contraseña usando el token enviado por correo."""
    from jose import JWTError, jwt
    from .security import SECRET_KEY, ALGORITHM

    try:
        token_data = jwt.decode(payload.token, SECRET_KEY, algorithms=[ALGORITHM])
        correo = token_data.get("sub")
        token_type = token_data.get("type")

        if not correo or token_type != "password_reset":
            raise HTTPException(status_code=400, detail="Token inválido")

    except JWTError:
        raise HTTPException(status_code=400, detail="Token inválido o expirado")

    user = db.query(models.Usuario).filter(models.Usuario.Correo == correo).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Actualizar contraseña
    user.Password = get_password_hash(payload.nueva_password)
    db.commit()

    return {"message": "Contraseña actualizada exitosamente. Ya puedes iniciar sesión."}

