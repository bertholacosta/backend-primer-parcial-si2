import sys
from datetime import date
from sqlalchemy.exc import IntegrityError

from src.database import SessionLocal, engine, Base
from src import models
from src.security import get_password_hash

# Create tables if they don't exist
models.Base.metadata.create_all(bind=engine)

def seed():
    db = SessionLocal()

    # Define roles
    roles_data = ["Administrador", "Conductor", "Taller"]
    for role_name in roles_data:
        rol = db.query(models.Rol).filter(models.Rol.Nombre == role_name).first()
        if not rol:
            rol = models.Rol(Nombre=role_name)
            db.add(rol)
    db.commit()

    # Define permisos
    permisos_data = ["Ver Dashboard", "Ver Usuarios", "Gestionar Roles", "Ver Mantenimientos", "Ver Taller", "Ver Vehiculos"]
    for perm_name in permisos_data:
        perm = db.query(models.Permiso).filter(models.Permiso.Nombre == perm_name).first()
        if not perm:
            perm = models.Permiso(Nombre=perm_name)
            db.add(perm)
    db.commit()

    # Administrador
    admin_email = "admin@root.com"
    admin_rol = db.query(models.Rol).filter(models.Rol.Nombre == "Administrador").first()
    admin_user = db.query(models.Usuario).filter(models.Usuario.Correo == admin_email).first()
    if not admin_user:
        admin_user = models.Usuario(
            Correo=admin_email,
            Password=get_password_hash("admin123"),
            IdRol=admin_rol.Id
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        admin_profile = models.Administrador(
            IdUsuario=admin_user.Id,
            Usuario="Super Admin"
        )
        db.add(admin_profile)
        db.commit()
        print(f"Admin created: {admin_email} / admin123")

    # Conductor
    cond_email = "conductor@root.com"
    cond_rol = db.query(models.Rol).filter(models.Rol.Nombre == "Conductor").first()
    cond_user = db.query(models.Usuario).filter(models.Usuario.Correo == cond_email).first()
    if not cond_user:
        cond_user = models.Usuario(
            Correo=cond_email,
            Password=get_password_hash("conductor123"),
            IdRol=cond_rol.Id
        )
        db.add(cond_user)
        db.commit()
        db.refresh(cond_user)

        cond_profile = models.Conductor(
            IdUsuario=cond_user.Id,
            CI="12345678",
            Nombre="Juan",
            Apellidos="Perez",
            Fechanac=date(1990, 1, 1)
        )
        db.add(cond_profile)
        db.commit()
        print(f"Conductor created: {cond_email} / conductor123")

    # Taller
    taller_email = "taller@root.com"
    taller_rol = db.query(models.Rol).filter(models.Rol.Nombre == "Taller").first()
    taller_user = db.query(models.Usuario).filter(models.Usuario.Correo == taller_email).first()
    if not taller_user:
        taller_user = models.Usuario(
            Correo=taller_email,
            Password=get_password_hash("taller123"),
            IdRol=taller_rol.Id
        )
        db.add(taller_user)
        db.commit()
        db.refresh(taller_user)

        taller_profile = models.Taller(
            Nombre="AutoFix Center",
            Direccion="Avenida Siempre Viva 742",
            Coordenadas="-17.78,-63.18",
            Cap=5,
            Capmax=10,
            IdUsuario=taller_user.Id
        )
        db.add(taller_profile)
        db.commit()
        print(f"Taller created: {taller_email} / taller123")

    print("Seeding completed successfully!")
    db.close()

if __name__ == "__main__":
    seed()
