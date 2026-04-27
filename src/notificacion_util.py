from sqlalchemy.orm import Session
from .models import Notificacion, Usuario
from datetime import datetime
import requests
import os

def crear_notificacion(db: Session, usuario_id: int, titulo: str, descripcion: str):
    """
    Crea una notificación en la base de datos y opcionalmente envía un push via FCM.
    """
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    nueva_notificacion = Notificacion(
        titulo=titulo,
        descripcion=descripcion,
        usuario_id=usuario_id,
        fecha=fecha_actual,
        estado="No leída"
    )
    
    db.add(nueva_notificacion)
    db.commit()
    db.refresh(nueva_notificacion)
    
    # Intentar enviar notificación push si el usuario tiene un token FCM
    usuario = db.query(Usuario).filter(Usuario.Id == usuario_id).first()
    if usuario and usuario.fcm_token:
        enviar_push_fcm(usuario.fcm_token, titulo, descripcion)
        
    return nueva_notificacion

def enviar_push_fcm(fcm_token: str, titulo: str, body: str):
    """
    Simulación de envío de notificación push via Firebase Cloud Messaging.
    En una implementación real, se usaría la API de FCM (v1) con service account.
    """
    print(f"[PUSH] Enviando a token {fcm_token[:10]}...: {titulo} - {body}")
    
    # Ejemplo de estructura para FCM v1 (requiere token de acceso de Google)
    # url = "https://fcm.googleapis.com/v1/projects/YOUR_PROJECT_ID/messages:send"
    # headers = { "Authorization": "Bearer ...", "Content-Type": "application/json" }
    # payload = { "message": { "token": fcm_token, "notification": { "title": titulo, "body": body } } }
    # try: requests.post(url, json=payload, headers=headers)
    pass
