import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = "gemini-2.5-flash"

_client = None


def _get_client():
    global _client
    if _client is None and GEMINI_API_KEY and GEMINI_API_KEY != "pon_tu_api_key_aqui":
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


def _leer_imagen(ruta_url: str) -> types.Part | None:
    """
    Convierte una URL local (/uploads/...) en un Part de imagen para Gemini.
    Devuelve None si el archivo no existe o no se puede leer.
    """
    # Normalizar la ruta: /uploads/... → uploads/... (relativa al CWD del servidor)
    ruta_local = ruta_url.lstrip("/")
    if not os.path.isfile(ruta_local):
        print(f"[AI] Imagen no encontrada en disco: {ruta_local}")
        return None
    try:
        with open(ruta_local, "rb") as f:
            datos = f.read()
        mime = "image/png" if ruta_local.endswith(".png") else "image/jpeg"
        return types.Part.from_bytes(data=datos, mime_type=mime)
    except Exception as e:
        print(f"[AI] Error leyendo imagen {ruta_local}: {e}")
        return None


def analizar_incidente(
    descripcion: str,
    audio_disponible: bool = False,
    fotos_urls: list[str] | None = None,
) -> dict:
    """
    Analiza un incidente vehicular usando descripción de texto + imágenes opcionales.

    Args:
        descripcion: Texto escrito/hablado por el conductor.
        audio_disponible: True si el conductor adjuntó un audio (enriquece el contexto).
        fotos_urls: Lista de URLs locales de fotos (/uploads/...) guardadas en disco.

    Returns dict con:
      - informacion_valida  : bool
      - Clasificacion       : str
      - NivelPrioridad      : "Alta" | "Media" | "Baja" | "Pendiente"
      - Resumen             : str (incluye recomendación de tipo de taller)
    """
    fallback_error = {
        "informacion_valida": True,
        "Clasificacion": "Sin clasificar",
        "NivelPrioridad": "Media",
        "Resumen": "No se pudo procesar el análisis automático.",
    }

    if not GEMINI_API_KEY or GEMINI_API_KEY == "pon_tu_api_key_aqui":
        print("[AI] GEMINI_API_KEY no configurada — análisis omitido.")
        return fallback_error

    client = _get_client()
    if not client:
        return fallback_error

    # ── Contexto adicional ──────────────────────────────────────────────────
    contexto_audio = (
        "\n⚠️ IMPORTANTE: El conductor también adjuntó un AUDIO describiendo el incidente. "
        "Considera que puede haber información adicional en ese audio (ruidos del motor, "
        "descripción verbal de daños, estado emocional) que complementa la descripción escrita."
        if audio_disponible
        else ""
    )

    imagenes_disponibles = fotos_urls and len(fotos_urls) > 0
    contexto_fotos = (
        f"\n🖼️ IMPORTANTE: El conductor adjuntó {len(fotos_urls)} foto(s). "
        "Analiza CUIDADOSAMENTE las imágenes adjuntas para detectar daños visibles, "
        "estado de las llantas, tablero, carrocería u otros indicadores visuales."
        if imagenes_disponibles
        else ""
    )

    prompt = f"""Eres un sistema experto en análisis de incidentes vehiculares.
Un conductor ha reportado un siniestro o emergencia.

Descripción del conductor: '{descripcion}'{contexto_audio}{contexto_fotos}

{'=== INSTRUCCIONES PARA ANÁLISIS VISUAL ===' if imagenes_disponibles else ''}
{'Examina las imágenes adjuntas y busca: daños en carrocería, llantas pinchadas o deformadas, ' if imagenes_disponibles else ''}
{'humo, líquidos en el suelo, tablero encendido con errores, estado general del vehículo.' if imagenes_disponibles else ''}

PASO 1 — Evalúa si la información es suficiente:
- Si la descripción tiene menos de 5 palabras Y no hay imágenes → informacion_valida: false
- Si hay imágenes, úsalas para complementar aunque la descripción sea corta
- Si hay audio disponible, asume que contiene información adicional relevante

PASO 2 — Clasifica el incidente según lo que observes/leas:
Tipos comunes: "Pinchazo de llanta", "Falla de batería / No enciende", "Colisión / Choque",
"Sobrecalentamiento del motor", "Falla mecánica general", "Accidente con lesionados",
"Vehículo atrapado / volcado", "Falla eléctrica"

PASO 3 — Asigna NivelPrioridad:
- Alta: riesgo para la vida, vehículo completamente inmovilizado en vía rápida, humo/fuego, heridos
- Media: vehículo inmovilizado en lugar seguro, daños moderados, sin lesionados
- Baja: daños menores, vehículo puede moverse, sin riesgo inmediato

PASO 4 — En el Resumen, incluye SIEMPRE una recomendación del tipo de taller:
- "Se recomienda un taller con servicio de auxilio eléctrico / diagnóstico a domicilio."
- "Se recomienda un taller con servicio de vulcanización móvil."
- "Se recomienda un taller con capacidad de remolque y reparación de chapa/pintura."
- "Se recomienda cualquier taller mecánico cercano."

Responde ÚNICAMENTE con un objeto JSON válido con esta estructura exacta:
{{
  "informacion_valida": true,
  "Clasificacion": "<tipo de incidente, máximo 60 caracteres>",
  "NivelPrioridad": "<exactamente uno de: Alta, Media, Baja>",
  "Resumen": "<2-3 oraciones: descripción del problema + recomendación de tipo de taller>"
}}

Si la información es insuficiente (sin imagen y descripción muy pobre):
{{
  "informacion_valida": false,
  "Clasificacion": "Información insuficiente",
  "NivelPrioridad": "Pendiente",
  "Resumen": "<explica qué información específica necesita el conductor agregar>"
}}

No incluyas ningún texto fuera del JSON. No uses bloques de código markdown."""

    # ── Construir contenido multimodal ──────────────────────────────────────
    parts: list[types.Part] = []

    # Agregar imágenes primero (máx. 4 para no saturar)
    if imagenes_disponibles:
        imagenes_agregadas = 0
        for url in fotos_urls[:4]:
            part = _leer_imagen(url)
            if part:
                parts.append(part)
                imagenes_agregadas += 1
        if imagenes_agregadas > 0:
            print(f"[AI] {imagenes_agregadas} imagen(es) enviadas a Gemini para análisis visual")

    # Agregar el prompt de texto al final
    parts.append(types.Part.from_text(text=prompt))

    try:
        if len(parts) == 1:
            # Solo texto → llamada simple
            response = client.models.generate_content(model=MODEL, contents=prompt)
        else:
            # Multimodal (texto + imágenes)
            response = client.models.generate_content(
                model=MODEL,
                contents=[types.Content(role="user", parts=parts)],
            )

        raw = response.text.strip()

        # Limpiar bloques markdown si los hubiera
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        data = json.loads(raw)

        es_valida = bool(data.get("informacion_valida", True))
        nivel = data.get("NivelPrioridad", "Media")
        if nivel not in ("Alta", "Media", "Baja", "Pendiente"):
            nivel = "Media"

        return {
            "informacion_valida": es_valida,
            "Clasificacion": str(data.get("Clasificacion", "Sin clasificar"))[:100],
            "NivelPrioridad": nivel,
            "Resumen": str(data.get("Resumen", ""))[:2000],
        }

    except json.JSONDecodeError as e:
        print(f"[AI] Error parseando JSON de Gemini: {e} — respuesta: {raw!r}")
        return {
            "informacion_valida": True,
            "Clasificacion": "Sin clasificar",
            "NivelPrioridad": "Media",
            "Resumen": "El análisis automático no pudo procesarse correctamente.",
        }
    except Exception as e:
        print(f"[AI] Error inesperado al analizar incidente: {e}")
        return {
            "informacion_valida": True,
            "Clasificacion": "Sin clasificar",
            "NivelPrioridad": "Media",
            "Resumen": "Ocurrió un error al procesar el análisis de IA.",
        }
