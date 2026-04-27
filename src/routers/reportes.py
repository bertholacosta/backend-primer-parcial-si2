from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any
from datetime import datetime, timedelta

from ..database import get_db
from ..models import Incidente, Taller, Pago, Usuario
from ..deps import get_current_user

router = APIRouter(
    prefix="/reportes",
    tags=["Reportes y Estadísticas"]
)

@router.get("/taller/stats")
def get_taller_stats(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtiene estadísticas generales para el taller del usuario logueado.
    """
    if not current_user.talleres:
        raise HTTPException(status_code=403, detail="Solo talleres pueden ver sus reportes")
    
    taller = current_user.talleres[0]
    
    # 1. Conteo de incidentes por estado
    stats_estado = db.query(
        Incidente.estado, 
        func.count(Incidente.id)
    ).filter(Incidente.taller_id == taller.Id).group_by(Incidente.estado).all()
    
    estado_dict = {estado: count for estado, count in stats_estado}
    
    # 2. Ingresos totales (Pagos completados)
    total_ingresos = db.query(func.sum(Pago.monto_total)).join(Incidente).filter(
        Incidente.taller_id == taller.Id,
        Pago.estado == "Completado"
    ).scalar() or 0
    
    # 3. Incidentes en los últimos 7 días (para gráfico lineal)
    hoy = datetime.now()
    hace_7_dias = hoy - timedelta(days=7)
    
    # Nota: La fecha en Incidente es String "%Y-%m-%d %H:%M:%S"
    # Esto complica un poco la query pura SQL si no usamos cast, pero podemos filtrar en memoria o con Like
    incidentes_recientes = db.query(Incidente).filter(
        Incidente.taller_id == taller.Id,
        Incidente.fecha >= hace_7_dias.strftime("%Y-%m-%d")
    ).all()
    
    # Agrupar por día
    series_incidentes = {}
    for i in range(7):
        dia = (hoy - timedelta(days=i)).strftime("%Y-%m-%d")
        series_incidentes[dia] = 0
        
    for inc in incidentes_recientes:
        dia_inc = inc.fecha[:10]
        if dia_inc in series_incidentes:
            series_incidentes[dia_inc] += 1
            
    # Formatear para el frontend (lista ordenada de objetos)
    chart_data = [{"fecha": k, "cantidad": v} for k, v in sorted(series_incidentes.items())]

    return {
        "resumen": {
            "total_incidentes": sum(estado_dict.values()),
            "resueltos": estado_dict.get("Resuelto", 0) + estado_dict.get("Pagado", 0),
            "pendientes": estado_dict.get("Asignado", 0) + estado_dict.get("En Camino", 0),
            "ingresos_totales": total_ingresos,
            "balance_plataforma": taller.balance
        },
        "por_estado": estado_dict,
        "historico_7_dias": chart_data
    }

@router.get("/taller/export/{format}")
def export_taller_data(
    format: str,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Exporta la lista de incidentes del taller en formato CSV, XML o PDF.
    """
    if not current_user.talleres:
        raise HTTPException(status_code=403, detail="Solo talleres pueden exportar sus datos")
    
    taller = current_user.talleres[0]
    
    # Obtener todos los incidentes con detalles de pago
    incidentes = db.query(Incidente).filter(Incidente.taller_id == taller.Id).all()
    
    import pandas as pd
    import io
    from fastapi.responses import StreamingResponse, Response

    data = []
    for inc in incidentes:
        # Buscar pago asociado si existe
        pago = db.query(Pago).filter(Pago.incidente_id == inc.id, Pago.estado == "Completado").first()
        data.append({
            "ID": inc.id,
            "Fecha": inc.fecha,
            "Estado": inc.estado,
            "Coordenadas": inc.coordenadagps,
            "Monto": pago.monto_total if pago else 0,
            "Metodo Pago": pago.metodo if pago else "N/A"
        })
    
    df = pd.DataFrame(data)
    
    if format == "csv":
        stream = io.StringIO()
        df.to_csv(stream, index=False)
        response = StreamingResponse(iter([stream.getvalue()]), media_type="text/csv")
        response.headers["Content-Disposition"] = f"attachment; filename=reporte_taller_{taller.Id}.csv"
        return response
        
    elif format == "xml":
        xml_data = df.to_xml(index=False)
        return Response(content=xml_data, media_type="application/xml", headers={
            "Content-Disposition": f"attachment; filename=reporte_taller_{taller.Id}.xml"
        })
        
    elif format == "pdf":
        # Para PDF, usaremos una representación simple de texto para evitar dependencias pesadas
        # o instalaremos fpdf si el usuario lo permite. Por ahora, generamos un reporte detallado en texto.
        try:
            from fpdf import FPDF
        except ImportError:
            # Si no está instalado, devolvemos un error informativo o usamos una alternativa
            raise HTTPException(status_code=501, detail="Exportación a PDF requiere la librería 'fpdf2'. Instálala con 'pip install fpdf2'.")

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(40, 10, f"Reporte de Taller: {taller.Nombre}")
        pdf.ln(10)
        pdf.set_font("Arial", '', 10)
        pdf.cell(40, 10, f"Fecha de Generación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        pdf.ln(20)
        
        # Header
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(20, 10, "ID", 1)
        pdf.cell(40, 10, "Fecha", 1)
        pdf.cell(40, 10, "Estado", 1)
        pdf.cell(30, 10, "Monto", 1)
        pdf.ln()
        
        # Rows
        pdf.set_font("Arial", '', 10)
        for row in data:
            pdf.cell(20, 10, str(row["ID"]), 1)
            pdf.cell(40, 10, str(row["Fecha"][:10]), 1)
            pdf.cell(40, 10, str(row["Estado"]), 1)
            pdf.cell(30, 10, str(row["Monto"]), 1)
            pdf.ln()
            
        pdf_output = pdf.output(dest='S')
        return Response(content=pdf_output, media_type="application/pdf", headers={
            "Content-Disposition": f"attachment; filename=reporte_taller_{taller.Id}.pdf"
        })
        
    else:
        raise HTTPException(status_code=400, detail="Formato no soportado")
