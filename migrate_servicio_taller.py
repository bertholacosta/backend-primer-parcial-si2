"""Script de migración: crea la tabla ServicioTaller y carga datos de ejemplo."""
from src.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    # Crear tabla
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS "ServicioTaller" (
            id SERIAL PRIMARY KEY,
            nombre VARCHAR(100) NOT NULL,
            taller_id INTEGER NOT NULL REFERENCES "Taller"("Id") ON DELETE CASCADE
        )
    """))
    conn.commit()
    print("OK: Tabla 'ServicioTaller' creada")

    # Leer talleres existentes
    talleres = conn.execute(text('SELECT "Id", "Nombre" FROM "Taller" ORDER BY "Id"')).fetchall()
    print(f"Talleres encontrados: {len(talleres)}")

    # Servicios de ejemplo para cubrir los 4 casos de uso
    servicios_ejemplo = [
        "Mecánica General",
        "Auxilio Eléctrico",
        "Vulcanización Móvil",
        "Remolque",
        "Chapa y Pintura",
        "Diagnóstico a Domicilio",
    ]

    for i, taller in enumerate(talleres):
        taller_id = taller[0]
        # Asignar servicios rotativos para que haya variedad
        # Todos tienen Mecánica General; los demás se distribuyen
        servicios_a_asignar = ["Mecánica General"]
        if i % 3 == 0:
            servicios_a_asignar.append("Auxilio Eléctrico")
            servicios_a_asignar.append("Diagnóstico a Domicilio")
        if i % 3 == 1:
            servicios_a_asignar.append("Vulcanización Móvil")
            servicios_a_asignar.append("Remolque")
        if i % 3 == 2:
            servicios_a_asignar.append("Chapa y Pintura")
            servicios_a_asignar.append("Remolque")

        for nombre_svc in servicios_a_asignar:
            # Evitar duplicados
            existe = conn.execute(
                text('SELECT 1 FROM "ServicioTaller" WHERE taller_id=:tid AND nombre=:nom'),
                {"tid": taller_id, "nom": nombre_svc}
            ).fetchone()
            if not existe:
                conn.execute(
                    text('INSERT INTO "ServicioTaller" (nombre, taller_id) VALUES (:nom, :tid)'),
                    {"nom": nombre_svc, "tid": taller_id}
                )
        conn.commit()
        print(f"  Taller #{taller_id} ({taller[1]}): {servicios_a_asignar}")

    print("OK: Datos de ejemplo insertados en ServicioTaller")
