"""Canal WhatsApp vía YCloud: parseo del webhook entrante + envío de mensajes.

Reemplaza los nodos n8n: Webhook (parse whatsappInboundMessage) + HTTP Request2 (send).

- `parsear_inbound(body)` → dict normalizado del mensaje entrante.
- `verificar_firma(raw, header)` → valida 'ycloud-signature' si hay secreto configurado.
- `enviar(destino, origen, texto)` → POST a YCloud sendDirectly.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Any, Optional

import httpx

from ...config import settings
from .. import credentials as creds_service

log = logging.getLogger("agente_externo.ycloud")


def _api_key() -> str:
    return creds_service.get("YCLOUD_API_KEY", settings.YCLOUD_API_KEY) or ""


# ── Parseo del inbound ────────────────────────────────────────────────────────
def parsear_inbound(body: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Extrae los campos del `whatsappInboundMessage`. None si no es un mensaje entrante."""
    msg = (body or {}).get("whatsappInboundMessage")
    if not isinstance(msg, dict):
        return None
    perfil = msg.get("customerProfile") or {}
    tipo = msg.get("type") or "text"
    link = ""
    mime = ""
    for k in ("audio", "image", "video", "document"):
        media = msg.get(k)
        if isinstance(media, dict) and media.get("link"):
            link = media.get("link") or ""
            mime = media.get("mime_type") or ""
            break
    return {
        "id": msg.get("id"),
        "usuario": msg.get("from"),                 # +tel del cliente (session id)
        "nosotros": msg.get("to"),                  # +nuestro número
        "nombre": perfil.get("name") or msg.get("from"),
        "tipo": tipo,                               # text|audio|image|video|document
        "texto": (msg.get("text") or {}).get("body") or "",
        "media_link": link,
        "media_mime": mime,
    }


# ── Verificación de firma (opcional) ──────────────────────────────────────────
def verificar_firma(raw_body: bytes, header: Optional[str]) -> bool:
    """Valida 'ycloud-signature: t=...,s=...' con HMAC-SHA256(secret, '{t}.{body}').

    Si no hay secreto configurado, no se verifica (devuelve True).
    """
    secret = creds_service.get("YCLOUD_WEBHOOK_SECRET", settings.YCLOUD_WEBHOOK_SECRET) or ""
    if not secret:
        return True
    if not header:
        return False
    partes = dict(
        p.split("=", 1) for p in header.split(",") if "=" in p
    )
    t = partes.get("t", "")
    s = partes.get("s", "")
    if not (t and s):
        return False
    firmado = f"{t}.".encode() + raw_body
    esperado = hmac.new(secret.encode(), firmado, hashlib.sha256).hexdigest()
    return hmac.compare_digest(esperado, s)


# ── Envío ─────────────────────────────────────────────────────────────────────
def enviar(destino: str, origen: str, texto: str) -> bool:
    """Envía un mensaje de texto por YCloud. Devuelve True si salió 2xx."""
    if not texto or not destino:
        return False
    key = _api_key()
    if not key:
        log.error("YCLOUD_API_KEY no configurada — no se puede enviar")
        return False
    payload = {"type": "text", "text": {"body": texto}, "from": origen, "to": destino}
    headers = {"accept": "application/json", "Content-Type": "application/json", "X-API-Key": key}
    try:
        r = httpx.post(settings.YCLOUD_SEND_URL, json=payload, headers=headers, timeout=30)
        if r.status_code >= 300:
            log.warning("YCloud send %s: %s", r.status_code, r.text[:200])
            return False
        return True
    except Exception as e:  # noqa: BLE001
        log.warning("YCloud send excepción: %s", e)
        return False


def descargar_media(link: str) -> Optional[bytes]:
    """Descarga un archivo de media de YCloud (header X-API-Key). None si falla."""
    if not link:
        return None
    try:
        r = httpx.get(link, headers={"X-API-Key": _api_key()}, timeout=60, follow_redirects=True)
        if r.status_code < 300:
            return r.content
    except Exception as e:  # noqa: BLE001
        log.warning("descargar_media falló: %s", e)
    return None
