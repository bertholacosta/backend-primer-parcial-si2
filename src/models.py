from sqlalchemy import Column, Integer, String, ForeignKey, Table, Date
from sqlalchemy.orm import relationship
from .database import Base

# Tabla intermedia para la relación muchos a muchos entre Rol y Permiso
rol_permiso_table = Table(
    'Rol_Permiso',
    Base.metadata,
    Column('IdRol', Integer, ForeignKey('Rol.Id'), primary_key=True),
    Column('IdPermiso', Integer, ForeignKey('Permiso.Id'), primary_key=True)
)

# Removido temporalmente para pasarlo a un Modelo de SQLAlchemy real.

class Permiso(Base):
    __tablename__ = 'Permiso'

    Id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    Nombre = Column(String(255), nullable=False)

    # Relación back_populates con Rol
    roles = relationship("Rol", secondary=rol_permiso_table, back_populates="permisos")


class Rol(Base):
    __tablename__ = 'Rol'

    Id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    Nombre = Column(String(255), nullable=False)

    # Relaciones
    permisos = relationship("Permiso", secondary=rol_permiso_table, back_populates="roles")
    usuarios = relationship("Usuario", back_populates="rol")


class Usuario(Base):
    __tablename__ = 'Usuario'

    Id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    Correo = Column(String(255), nullable=False, unique=True, index=True)
    Password = Column(String(255), nullable=False)
    IdRol = Column(Integer, ForeignKey('Rol.Id'), nullable=False)

    # Relaciones
    rol = relationship("Rol", back_populates="usuarios")
    talleres = relationship("Taller", back_populates="usuario")
    administrador = relationship("Administrador", uselist=False, back_populates="usuario")
    conductor = relationship("Conductor", uselist=False, back_populates="usuario")
    mecanico = relationship("Mecanico", uselist=False, back_populates="usuario")
    bitacoras = relationship("Bitacora", back_populates="usuario")

class Taller(Base):
    __tablename__ = 'Taller'
    
    Id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    Nombre = Column(String(255), nullable=False)
    Direccion = Column(String(255), nullable=False)
    Coordenadas = Column(String(255))
    Cap = Column(Integer)
    Capmax = Column(Integer)
    IdUsuario = Column(Integer, ForeignKey('Usuario.Id'), nullable=False)

    usuario = relationship("Usuario", back_populates="talleres")
    mecanicos = relationship("Mecanico", back_populates="taller")


class Administrador(Base):
    __tablename__ = 'Administrador'
    
    IdUsuario = Column(Integer, ForeignKey('Usuario.Id'), primary_key=True)
    Usuario = Column(String(255), nullable=False)

    usuario = relationship("Usuario", back_populates="administrador")


class Conductor(Base):
    __tablename__ = 'Conductor'
    
    IdUsuario = Column(Integer, ForeignKey('Usuario.Id'), primary_key=True)
    CI = Column(String(50), nullable=False)
    Nombre = Column(String(255), nullable=False)
    Apellidos = Column(String(255), nullable=False)
    Fechanac = Column(Date, nullable=False)

    usuario = relationship("Usuario", back_populates="conductor")
    vehiculos = relationship("Vehiculo", secondary="VehiculoConductor", back_populates="conductores")
    vehiculo_conductores = relationship("VehiculoConductor", back_populates="conductor")


class Vehiculo(Base):
    __tablename__ = 'Vehiculo'
    
    Id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    Marca = Column(String(100))
    Modelo = Column(String(100))
    Placa = Column(String(50), unique=True)
    Poliza = Column(String(100))
    Categoria = Column(String(100))
    Año = Column(Integer)
    conductores = relationship("Conductor", secondary="VehiculoConductor", back_populates="vehiculos")
    vehiculo_conductores = relationship("VehiculoConductor", back_populates="vehiculo")

class VehiculoConductor(Base):
    __tablename__ = 'VehiculoConductor'

    id = Column(Integer, primary_key=True, autoincrement=True)
    fechareg = Column(String(50)) # Fecha como string provisional o DateTime
    conductor_id = Column(Integer, ForeignKey('Conductor.IdUsuario', ondelete="CASCADE"), nullable=False)
    vehiculo_id = Column(Integer, ForeignKey('Vehiculo.Id', ondelete="CASCADE"), nullable=False)

    conductor = relationship("Conductor", back_populates="vehiculo_conductores")
    vehiculo = relationship("Vehiculo", back_populates="vehiculo_conductores")
    incidentes = relationship("Incidente", back_populates="vehiculoconductor")

class Incidente(Base):
    __tablename__ = 'Incidente'

    id = Column(Integer, primary_key=True, autoincrement=True)
    coordenadagps = Column(String(255))
    estado = Column(String(50), default="Reportado")
    fecha = Column(String(50))
    vehiculoconductor_id = Column(Integer, ForeignKey('VehiculoConductor.id', ondelete="CASCADE"), nullable=False)
    taller_id = Column(Integer, ForeignKey('Taller.Id', ondelete="SET NULL"), nullable=True)

    vehiculoconductor = relationship("VehiculoConductor", back_populates="incidentes")
    evidencias = relationship("Evidencia", back_populates="incidente", cascade="all, delete-orphan")
    taller = relationship("Taller", foreign_keys=[taller_id])

class Evidencia(Base):
    __tablename__ = 'Evidencia'

    id = Column(Integer, primary_key=True, autoincrement=True)
    audio = Column(String(2000), nullable=True) 
    descripcion = Column(String(5000), nullable=True)
    fotos = Column(String(2000), nullable=True)  # Puede ser una trama separada por comas de urls/base64
    incidente_id = Column(Integer, ForeignKey('Incidente.id', ondelete="CASCADE"), nullable=False)

    incidente = relationship("Incidente", back_populates="evidencias")

class Mecanico(Base):
    __tablename__ = 'Mecanico'
    
    id = Column(Integer, ForeignKey('Usuario.Id', ondelete="CASCADE"), primary_key=True)
    ci = Column(Integer, nullable=False)
    extci = Column(String(2))
    nombre = Column(String(255), nullable=False)
    apellidos = Column(String(255), nullable=False)
    fechanac = Column(Integer)
    taller_id = Column(Integer, ForeignKey('Taller.Id', ondelete="SET NULL"), nullable=True)

    usuario = relationship("Usuario", back_populates="mecanico")
    taller = relationship("Taller", back_populates="mecanicos")


class Bitacora(Base):
    __tablename__ = 'Bitacora'

    id = Column(Integer, primary_key=True, autoincrement=True)
    accion = Column(String(255))
    descripcion = Column(String(255))
    fecha = Column(Date)
    ip = Column(String(255))
    usuario_id = Column(Integer, ForeignKey('Usuario.Id', ondelete="CASCADE"))

    usuario = relationship("Usuario", back_populates="bitacoras")
