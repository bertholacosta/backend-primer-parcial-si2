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
def _leer_audio(ruta_url: str) -> types.Part | None:
    """
    Convierte una URL local (/uploads/...) en un Part de audio para Gemini.
    """
    ruta_local = ruta_url.lstrip("/")
    if not os.path.isfile(ruta_local):
        return None
    try:
        with open(ruta_local, "rb") as f:
            datos = f.read()
        return types.Part.from_bytes(data=datos, mime_type="audio/mpeg") # m4a/aac suelen ser mpeg
    except Exception as e:
        print(f"[AI] Error leyendo audio {ruta_local}: {e}")
        return None


def analizar_incidente(
    descripcion: str,
    audio_url: str | None = None,
    fotos_urls: list[str] | None = None,
) -> dict:
    """
    Analiza un incidente vehicular usando descripción de texto + audio + imágenes.

    Returns dict con:
      - informacion_valida  : bool
      - Clasificacion       : str
      - NivelPrioridad      : "Alta" | "Media" | "Baja" | "Pendiente"
      - Resumen             : str
      - Transcripcion       : str (transcripción literal del audio)
    """
    fallback_error = {
        "informacion_valida": True,
        "Clasificacion": "Sin clasificar",
        "NivelPrioridad": "Media",
        "Resumen": "No se pudo procesar el análisis automático.",
        "Transcripcion": ""
    }

    if not GEMINI_API_KEY or GEMINI_API_KEY == "pon_tu_api_key_aqui":
        print("[AI] GEMINI_API_KEY no configurada — análisis omitido.")
        return fallback_error

    client = _get_client()
    if not client:
        return fallback_error

    # ── Contexto adicional ──────────────────────────────────────────────────
    audio_disponible = bool(audio_url)
    contexto_audio = (
        "\n🎙️ IMPORTANTE: Se ha adjuntado un ARCHIVO DE AUDIO. "
        "Escucha el audio adjunto, TRANSCRÍBELO literalmente y úsalo como fuente principal "
        "de información junto con la descripción escrita."
        if audio_disponible
        else ""
    )

    imagenes_disponibles = fotos_urls and len(fotos_urls) > 0
    contexto_fotos = (
        f"\n🖼️ IMPORTANTE: Hay {len(fotos_urls)} foto(s). "
        "Analiza las imágenes para detectar daños visibles o fallas en el tablero."
        if imagenes_disponibles
        else ""
    )

    prompt = f"""Eres un experto en análisis de incidentes vehiculares.
Analiza la descripción, el audio y las fotos para dar un diagnóstico preciso.

Descripción: '{descripcion}'{contexto_audio}{contexto_fotos}

INSTRUCCIONES:
1. TRANSCRIPCIÓN: Si hay un archivo de audio, transcríbelo palabra por palabra.
2. VALIDACIÓN: Si no hay información suficiente (ni audio, ni fotos, ni texto claro) → informacion_valida: false.
3. CLASIFICACIÓN: Identifica el tipo de problema (Ej: "Falla de Motor", "Pinchazo", "Choque").
4. PRIORIDAD: Asigna Alta, Media o Baja según la gravedad.
5. RESUMEN: Breve explicación y recomendación de taller.

Responde ÚNICAMENTE con un objeto JSON:
{{
  "informacion_valida": true,
  "Clasificacion": "...",
  "NivelPrioridad": "...",
  "Resumen": "...",
  "Transcripcion": "<texto literal del audio o vacío si no hay audio>"
}}"""

    # ── Construir contenido multimodal ──────────────────────────────────────
    parts: list[types.Part] = []

    # 1. Agregar Audio
    if audio_disponible:
        audio_part = _leer_audio(audio_url)
        if audio_part:
            parts.append(audio_part)

    # 2. Agregar Imágenes (máx 4)
    if imagenes_disponibles:
        for url in fotos_urls[:4]:
            img_part = _leer_imagen(url)
            if img_part:
                parts.append(img_part)

    # 3. Agregar Prompt
    parts.append(types.Part.from_text(text=prompt))

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=[types.Content(role="user", parts=parts)],
        )

        raw = response.text.strip()
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"): raw = raw[4:]
            raw = raw.strip()

        data = json.loads(raw)

        return {
            "informacion_valida": bool(data.get("informacion_valida", True)),
            "Clasificacion": str(data.get("Clasificacion", "Sin clasificar"))[:100],
            "NivelPrioridad": data.get("NivelPrioridad", "Media"),
            "Resumen": str(data.get("Resumen", ""))[:2000],
            "Transcripcion": str(data.get("Transcripcion", ""))
        }
oridad": "Pendiente",
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
