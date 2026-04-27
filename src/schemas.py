from pydantic import BaseModel
from typing import List, Optional
from datetime import date

# --- Esquemas de Autenticación ---
class Token(BaseModel):
    access_token: str
    token_type: str
    role: Optional[str] = None
    permisos: Optional[List[str]] = []

class TokenData(BaseModel):
    correo: Optional[str] = None

class PasswordResetRequest(BaseModel):
    correo: str

class PasswordReset(BaseModel):
    token: str
    nueva_password: str

class MensajeResponse(BaseModel):
    message: str

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

class UsuarioUpdate(BaseModel):
    Correo: Optional[str] = None
    Password: Optional[str] = None
    IdRol: Optional[int] = None

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
    pass

class Vehiculo(VehiculoBase):
    Id: int

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

class TallerRegistro(TallerBase):
    Correo: str
    Password: str

# --- Esquemas para Mecanico ---
class MecanicoBase(BaseModel):
    ci: int
    extci: Optional[str] = None
    nombre: str
    apellidos: str
    fechanac: Optional[int] = None

class MecanicoUpdate(BaseModel):
    ci: Optional[int] = None
    extci: Optional[str] = None
    nombre: Optional[str] = None
    apellidos: Optional[str] = None
    fechanac: Optional[int] = None
    estado: Optional[str] = None

class MecanicoRegistro(MecanicoBase):
    correo: str
    password: str

class MecanicoOut(MecanicoBase):
    id: int
    taller_id: Optional[int] = None
    estado: str = "Disponible"

    class Config:
        from_attributes = True

# --- Esquemas para Incidentes y Evidencias ---
class EvidenciaBase(BaseModel):
    audio: Optional[str] = None
    descripcion: Optional[str] = None
    fotos: Optional[str] = None

class EvidenciaCreate(EvidenciaBase):
    pass

class Evidencia(EvidenciaBase):
    id: int
    incidente_id: int

    class Config:
        from_attributes = True

class IncidenteBase(BaseModel):
    coordenadagps: Optional[str] = None
    estado: Optional[str] = "Reportado"
    fecha: Optional[str] = None

class IncidenteCreate(IncidenteBase):
    vehiculo_id: int # El frontend nos pasará el vehículo afectado. Buscarémos el vehiculoconductor correspondiente.
    evidencia: EvidenciaBase

class Incidente(IncidenteBase):
    id: int
    vehiculoconductor_id: int
    taller_id: Optional[int] = None
    evidencias: List[Evidencia] = []

    class Config:
        from_attributes = True

# --- Esquemas para Gestión de Solicitudes ---
class TallerDisponible(BaseModel):
    Id: int
    Nombre: str
    Direccion: str
    Coordenadas: Optional[str] = None
    Cap: Optional[int] = None
    Capmax: Optional[int] = None
    distancia_km: Optional[float] = None

    class Config:
        from_attributes = True

class TallerEnIncidente(BaseModel):
    Id: int
    Nombre: str
    Direccion: str
    Coordenadas: Optional[str] = None

    class Config:
        from_attributes = True

class AnalisisIAEnIncidente(BaseModel):
    Clasificacion: Optional[str] = None
    NivelPrioridad: Optional[str] = None
    Resumen: Optional[str] = None

    class Config:
        from_attributes = True

# --- Esquemas para Cotización ---
class CotizacionBase(BaseModel):
    monto: Optional[int] = None
    mensaje: Optional[str] = None
    estado: str = "Solicitada"
    fecha_creacion: Optional[str] = None
    incidente_id: int
    taller_id: int

class CotizacionCreate(BaseModel):
    taller_id: int

class CotizacionOfrecer(BaseModel):
    monto: int
    mensaje: Optional[str] = None

class CotizacionOut(CotizacionBase):
    id: int
    taller: Optional[TallerEnIncidente] = None

    class Config:
        from_attributes = True

class IncidenteDetalle(IncidenteBase):
    id: int
    vehiculoconductor_id: int
    taller_id: Optional[int] = None
    evidencias: List[Evidencia] = []
    taller: Optional[TallerEnIncidente] = None
    analisis_ia: Optional[AnalisisIAEnIncidente] = None
    cotizaciones: List[CotizacionOut] = []
    mecanicos: List[MecanicoOut] = []

    class Config:
        from_attributes = True

class IncidentePendiente(IncidenteDetalle):
    distancia_km: Optional[float] = None

class AsignarTaller(BaseModel):
    taller_id: int

class AsignarMecanicos(BaseModel):
    mecanico_ids: List[int]

# --- Esquemas para Bitacora ---
class BitacoraBase(BaseModel):
    accion: Optional[str] = None
    descripcion: Optional[str] = None

class BitacoraOut(BitacoraBase):
    id: int
    fecha: Optional[date] = None
    ip: Optional[str] = None
    usuario_id: Optional[int] = None
    usuario_correo: Optional[str] = None
    usuario_rol: Optional[str] = None

    class Config:
        from_attributes = True

# --- Esquemas para Notificacion ---
class NotificacionBase(BaseModel):
    descripcion: Optional[str] = None
    estado: Optional[str] = "No leída"
    fecha: Optional[str] = None
    titulo: Optional[str] = None

class NotificacionCreate(NotificacionBase):
    pass

class NotificacionOut(NotificacionBase):
    id: int
    usuario_id: int

    class Config:
        from_attributes = True

class FCMTokenUpdate(BaseModel):
    fcm_token: str

# --- Esquemas para Perfil de Usuario ---
class AdminProfileData(BaseModel):
    Usuario: Optional[str] = None

    class Config:
        from_attributes = True

class TallerProfileData(BaseModel):
    Id: Optional[int] = None
    Nombre: Optional[str] = None
    Direccion: Optional[str] = None
    Coordenadas: Optional[str] = None
    Cap: Optional[int] = None
    Capmax: Optional[int] = None
    balance: Optional[int] = None

    class Config:
        from_attributes = True

class ConductorProfileData(BaseModel):
    CI: Optional[str] = None
    Nombre: Optional[str] = None
    Apellidos: Optional[str] = None
    Fechanac: Optional[date] = None

    class Config:
        from_attributes = True

class MecanicoProfileData(BaseModel):
    id: Optional[int] = None
    ci: Optional[int] = None
    nombre: Optional[str] = None
    apellidos: Optional[str] = None
    estado: Optional[str] = None

    class Config:
        from_attributes = True

class ProfileOut(BaseModel):
    Id: int
    Correo: str
    rol_nombre: Optional[str] = None
    administrador: Optional[AdminProfileData] = None
    taller: Optional[TallerProfileData] = None
    conductor: Optional[ConductorProfileData] = None
    mecanico: Optional[MecanicoProfileData] = None

    class Config:
        from_attributes = True

class ProfileUpdate(BaseModel):
    Correo: Optional[str] = None
    Password: Optional[str] = None
    # Datos de Administrador
    admin_usuario: Optional[str] = None
    # Datos de Taller
    taller_nombre: Optional[str] = None
    taller_direccion: Optional[str] = None
    taller_coordenadas: Optional[str] = None
    taller_cap: Optional[int] = None
    taller_capmax: Optional[int] = None
    # Datos de Conductor
    conductor_ci: Optional[str] = None
    conductor_nombre: Optional[str] = None
    conductor_apellidos: Optional[str] = None
    conductor_fechanac: Optional[date] = None
    mecanico_estado: Optional[str] = None

class UbicacionUpdate(BaseModel):
    Coordenadas: str
    Direccion: Optional[str] = None

class PagoOut(BaseModel):
    id: int
    monto_total: int
    metodo: str
    estado: str
    fecha: Optional[str] = None
    incidente_id: int
    stripe_session_id: Optional[str] = None

    class Config:
        from_attributes = True