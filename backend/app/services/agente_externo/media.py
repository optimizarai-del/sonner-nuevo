"""Transcripción de audio (Whisper) y análisis de imagen (visión) para el agente externo.

Reemplaza los nodos n8n: Descargar/Transcribir Audio y Descargar/Analyze image.
Entrada: bytes del archivo (ya descargado de YCloud). Salida: texto para el agente,
envuelto en <audio>…</audio> o <image>…</image> (igual que n8n).
"""
from __future__ import annotations

import base64
import io
import logging
from typing import Optional

from ...config import settings

log = logging.getLogger("agente_externo.media")

_PROMPT_IMG = (
    "Describe la imagen en detalle. Si contiene texto, transcribilo. Si es algo relevante "
    "para un evento (materiales, equipo de sonido/iluminación, salón, plano), describí qué es."
)


def _client():
    from openai import OpenAI
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY no configurada")
    return OpenAI(api_key=settings.OPENAI_API_KEY, timeout=60, max_retries=1)


def transcribir_audio(data: bytes, mime: str = "audio/ogg") -> str:
    """Devuelve '<audio>\\n {texto}\\n</audio>' o '' si falla."""
    if not data:
        return ""
    try:
        ext = "ogg"
        if mime and "/" in mime:
            ext = mime.split("/")[-1].split(";")[0] or "ogg"
        buf = io.BytesIO(data)
        buf.name = f"audio.{ext}"
        r = _client().audio.transcriptions.create(model="whisper-1", file=buf)
        texto = (getattr(r, "text", "") or "").strip()
        return f"<audio>\n {texto}\n</audio>" if texto else ""
    except Exception as e:  # noqa: BLE001
        log.warning("transcribir_audio falló: %s", e)
        return ""


def analizar_imagen(data: bytes, mime: str = "image/jpeg") -> str:
    """Devuelve '<image>\\n {descripcion}\\n</image>' o '' si falla."""
    if not data:
        return ""
    try:
        b64 = base64.b64encode(data).decode()
        url = f"data:{mime or 'image/jpeg'};base64,{b64}"
        r = _client().chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": _PROMPT_IMG},
                    {"type": "image_url", "image_url": {"url": url}},
                ],
            }],
            max_tokens=500,
        )
        desc = (r.choices[0].message.content or "").strip()
        return f"<image>\n {desc}\n</image>" if desc else ""
    except Exception as e:  # noqa: BLE001
        log.warning("analizar_imagen falló: %s", e)
        return ""


def a_texto(inbound: dict) -> Optional[str]:
    """Convierte un inbound (text/audio/image/otro) al texto que procesa el agente.

    Devuelve None si el tipo no se procesa (video/document/otro) → se ignora, como n8n.
    """
    tipo = (inbound or {}).get("tipo") or "text"
    if tipo == "text":
        return inbound.get("texto") or ""
    if tipo == "audio":
        data = _descargar(inbound)
        return transcribir_audio(data, inbound.get("media_mime") or "audio/ogg") if data else ""
    if tipo == "image":
        data = _descargar(inbound)
        return analizar_imagen(data, inbound.get("media_mime") or "image/jpeg") if data else ""
    return None


def _descargar(inbound: dict) -> Optional[bytes]:
    from .canal_ycloud import descargar_media
    return descargar_media(inbound.get("media_link") or "")
