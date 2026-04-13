from pydantic import BaseModel
from typing import List, Optional
from datetime import date

# --- Esquemas de Autenticación ---
class Token(BaseModel):
    access_token: str
    token_type: str
    role: Optional[str] = None

class TokenData(BaseModel):
    correo: Optional[str] = None

# --- Esquemas para Permiso ---
class PermisoBase(BaseModel):
    Nombre: str

class PermisoCreate(PermisoBase):
    pass

class Permiso(PermisoBase):
    Id: int

    class Config:
        from_attributes = True

# --- Esquemas para Rol ---
class RolBase(BaseModel):
    Nombre: str

class RolCreate(RolBase):
    pass

class Rol(RolBase):
    Id: int
    permisos: List[Permiso] = []

    class Config:
        from_attributes = True

# --- Esquemas para Usuario ---
class UsuarioBase(BaseModel):
    Correo: str
    IdRol: int

class UsuarioCreate(UsuarioBase):
    Password: str

class Usuario(UsuarioBase):
    Id: int
    # Incluimos información básica del rol asociado
    rol: Optional[Rol] = None

    class Config:
        from_attributes = True

# --- Esquemas para Administrador ---
class AdministradorBase(BaseModel):
    Usuario: str

class AdministradorCreate(AdministradorBase):
    IdUsuario: int

class Administrador(AdministradorBase):
    IdUsuario: int

    class Config:
        from_attributes = True

# --- Esquemas para Conductor ---
class ConductorBase(BaseModel):
    CI: str
    Nombre: str
    Apellidos: str
    Fechanac: date

class ConductorCreate(ConductorBase):
    IdUsuario: int

# Schema unificado especial para registro desde Flutter
class ConductorRegistro(BaseModel):
    Correo: str
    Password: str
    CI: str
    Nombre: str
    Apellidos: str
    Fechanac: date

class Conductor(ConductorBase):
    IdUsuario: int

    class Config:
        from_attributes = True

# --- Esquemas para Vehiculo ---
class VehiculoBase(BaseModel):
    Marca: Optional[str] = None
    Modelo: Optional[str] = None
    Placa: Optional[str] = None
    Poliza: Optional[str] = None
    Categoria: Optional[str] = None
    Año: Optional[int] = None

class VehiculoCreate(VehiculoBase):
    IdUsuario: int

class Vehiculo(VehiculoBase):
    Id: int
    IdUsuario: int

    class Config:
        from_attributes = True

# --- Esquemas para Taller ---
class TallerBase(BaseModel):
    Nombre: str
    Direccion: str
    Coordenadas: Optional[str] = None
    Cap: Optional[int] = None
    Capmax: Optional[int] = None

class TallerCreate(TallerBase):
    IdUsuario: int

class Taller(TallerBase):
    Id: int
    IdUsuario: int

    class Config:
        from_attributes = True
