import os
import stripe
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
import datetime

from ..database import get_db
from .. import models, schemas
from ..deps import get_current_user

router = APIRouter(
    prefix="/pagos",
    tags=["Pagos y Comisiones"]
)

# Se usará una clave de prueba por defecto si no existe en el entorno
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "sk_test_51MockTestKeyForDemoAppNoRealMoney123456789")

@router.post("/{incidente_id}/stripe")
def create_stripe_checkout(
    incidente_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    """Genera un link de Checkout de Stripe para pagar el incidente (100%)."""
    if not current_user.conductor:
        raise HTTPException(status_code=403, detail="Solo los conductores pueden pagar.")

    # Verificar incidente
    vc_ids = [vc.id for vc in current_user.conductor.vehiculo_conductores]
    incidente = db.query(models.Incidente).filter(
        models.Incidente.id == incidente_id, 
        models.Incidente.vehiculoconductor_id.in_(vc_ids)
    ).first()

    if not incidente:
        raise HTTPException(status_code=404, detail="Incidente no encontrado.")
    
    if incidente.estado != "Resuelto":
        raise HTTPException(status_code=400, detail="El incidente aún no está resuelto.")

    # Obtener monto de la cotización aceptada
    cotizacion = db.query(models.Cotizacion).filter(
        models.Cotizacion.incidente_id == incidente.id,
        models.Cotizacion.estado == "Aceptada"
    ).first()

    if not cotizacion or not cotizacion.monto:
        raise HTTPException(status_code=400, detail="No hay una cotización aceptada con monto válido.")

    monto_total = cotizacion.monto
    
    # Crear sesión de stripe
    # Para efectos del frontend local
    frontend_url = "http://localhost:4200"
    
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': f'Servicio de Mantenimiento - Incidente #{incidente_id}',
                        'description': f'Pago por servicio prestado en el taller',
                    },
                    'unit_amount': monto_total * 100, # Stripe usa centavos
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=f'{frontend_url}/pagos/success?session_id={{CHECKOUT_SESSION_ID}}&incidente_id={incidente_id}',
            cancel_url=f'{frontend_url}/pagos/cancel?incidente_id={incidente_id}',
        )
        
        # Registrar el pago como pendiente en la BD
        nuevo_pago = models.Pago(
            monto_total=monto_total,
            metodo="Stripe",
            estado="Pendiente",
            stripe_session_id=session.id,
            fecha=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            incidente_id=incidente_id
        )
        db.add(nuevo_pago)
        db.commit()
        
        return {"checkout_url": session.url}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{incidente_id}/directo", response_model=schemas.PagoOut)
def pago_directo(
    incidente_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    """Registra que el conductor pagó directamente al taller en efectivo/transferencia."""
    if not current_user.conductor:
        raise HTTPException(status_code=403, detail="Solo los conductores pueden pagar.")

    # Verificar incidente
    vc_ids = [vc.id for vc in current_user.conductor.vehiculo_conductores]
    incidente = db.query(models.Incidente).filter(
        models.Incidente.id == incidente_id, 
        models.Incidente.vehiculoconductor_id.in_(vc_ids)
    ).first()

    if not incidente:
        raise HTTPException(status_code=404, detail="Incidente no encontrado.")
    
    if incidente.estado != "Resuelto":
        raise HTTPException(status_code=400, detail="El incidente aún no está resuelto.")

    cotizacion = db.query(models.Cotizacion).filter(
        models.Cotizacion.incidente_id == incidente.id,
        models.Cotizacion.estado == "Aceptada"
    ).first()

    if not cotizacion or not cotizacion.monto:
        raise HTTPException(status_code=400, detail="Cotización no válida.")

    # Validar si ya hay un pago completado
    pago_previo = db.query(models.Pago).filter(models.Pago.incidente_id == incidente.id, models.Pago.estado == "Completado").first()
    if pago_previo:
        raise HTTPException(status_code=400, detail="Este servicio ya ha sido pagado.")

    monto_total = cotizacion.monto
    
    nuevo_pago = models.Pago(
        monto_total=monto_total,
        metodo="Directo",
        estado="Completado",
        fecha=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        incidente_id=incidente_id
    )
    db.add(nuevo_pago)
    
    # Lógica de Comisión
    # Pago Directo -> Taller cobra 100%, debe 10% a plataforma -> balance negativo para taller
    comision = int(monto_total * 0.10)
    taller = db.query(models.Taller).filter(models.Taller.Id == incidente.taller_id).first()
    if taller:
        taller.balance = (taller.balance or 0) - comision

    # Marcar incidente como Finalizado/Pagado
    incidente.estado = "Pagado"
    
    db.commit()
    db.refresh(nuevo_pago)
    
    return nuevo_pago

@router.post("/success", response_model=schemas.PagoOut)
def confirmar_pago_stripe(
    session_id: str,
    incidente_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    """El frontend llama aquí después del redireccionamiento exitoso de Stripe."""
    pago = db.query(models.Pago).filter(
        models.Pago.stripe_session_id == session_id,
        models.Pago.incidente_id == incidente_id
    ).first()

    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado.")
        
    if pago.estado == "Completado":
        return pago # Ya estaba verificado

    try:
        # Verificar con la API de Stripe
        session = stripe.checkout.Session.retrieve(session_id)
        if session.payment_status == 'paid':
            pago.estado = "Completado"
            
            # Lógica de Comisión
            # Pago Stripe -> Plataforma cobra 100%, se queda 10%, debe 90% a taller -> balance positivo para taller
            monto_taller = int(pago.monto_total * 0.90)
            
            incidente = db.query(models.Incidente).filter(models.Incidente.id == pago.incidente_id).first()
            if incidente:
                incidente.estado = "Pagado"
                taller = db.query(models.Taller).filter(models.Taller.Id == incidente.taller_id).first()
                if taller:
                    taller.balance = (taller.balance or 0) + monto_taller

            db.commit()
            db.refresh(pago)
            return pago
        else:
            raise HTTPException(status_code=400, detail="El pago en Stripe no fue completado exitosamente.")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
