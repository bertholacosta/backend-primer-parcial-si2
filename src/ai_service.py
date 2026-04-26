import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Inicializar cliente
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY and GEMINI_API_KEY != "pon_tu_api_key_aqui":
    genai.configure(api_key=GEMINI_API_KEY)
    
TEXT_MODEL = "gemini-1.5-flash"
VISION_MODEL = "gemini-1.5-flash"

def get_model(model_name: str):
    try:
        return genai.GenerativeModel(model_name)
    except Exception as e:
        print(f"Error cargando modelo Gemini: {e}")
        return None

def analizar_evidencia_visual(descripcion: str, imagen_url: str = None) -> str:
    """Analiza una imagen o descripción para estimar gravedad."""
    if not GEMINI_API_KEY or GEMINI_API_KEY == "pon_tu_api_key_aqui":
        return "⚠️ Configura GEMINI_API_KEY en tu archivo .env para habilitar el análisis por IA."

    model = get_model(VISION_MODEL)
    if not model:
         return "Error al cargar el modelo de IA."

    prompt = f"""
    Eres un ajustador de seguros experto y mecánico automotriz.
    El conductor ha reportado un incidente.
    Descripción proporcionada por el conductor: '{descripcion}'
    
    Por favor, analiza la situación y proporciona:
    1. Una estimación de la gravedad (Baja, Media, Alta).
    2. Posibles daños mecánicos ocultos a tener en cuenta.
    3. Recomendación inmediata para el taller.
    
    Devuelve la respuesta en un formato claro y profesional.
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error al procesar con IA: {str(e)}"

def generar_reporte_enriquecido(datos_incidente: dict) -> str:
    """Toma datos crudos y genera un reporte."""
    if not GEMINI_API_KEY or GEMINI_API_KEY == "pon_tu_api_key_aqui":
        return "⚠️ Configura GEMINI_API_KEY en tu archivo .env para habilitar la generación de reportes."

    model = get_model(TEXT_MODEL)
    if not model:
         return "Error al cargar el modelo de IA."

    prompt = f"""
    Eres un asistente administrativo del sistema de emergencias vehiculares.
    A partir de los siguientes datos estructurados de un incidente, redacta un breve 
    resumen ejecutivo de 1 párrafo para que el administrador entienda la situación de un vistazo.
    
    Datos del incidente:
    - ID: {datos_incidente.get('id')}
    - Estado: {datos_incidente.get('estado')}
    - Fecha: {datos_incidente.get('fecha')}
    - Taller Asignado ID: {datos_incidente.get('taller_id', 'Ninguno')}
    - Coordenadas: {datos_incidente.get('coordenadagps')}
    
    El tono debe ser profesional y directo al punto.
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
         return f"Error al generar reporte: {str(e)}"
