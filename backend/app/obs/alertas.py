"""Alertas deduplicadas por firma. Reemplaza el workflow `error trigger sonner`.

n8n mandaba un mail por CADA ejecución fallida: si el LLM se caía diez minutos, llegaban
cien mails iguales y nadie los leía. Acá cada error se reduce a una firma estable (tipo +
mensaje normalizado + nodo), se cuenta en `agent_errors` y solo se avisa por Telegram una
vez por ventana (`SONNER_ALERT_WINDOW_SECONDS`, 10 min por defecto).

Fail-safe total: si el alertador explota, se loguea y se sigue. Nunca tumba una corrida.
"""
from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from ..config import settings

log = logging.getLogger("obs.alertas")

# Lo que se borra del mensaje para que dos ocurrencias del mismo error compartan firma.
_VOLATIL = [
    re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I),  # uuid
    re.compile(r"\b\d{5,}\b"),          # ids largos, timestamps, teléfonos
    re.compile(r"0x[0-9a-f]+", re.I),   # direcciones de memoria
]


def _sb():
    from ..services import credentials as creds_service

    return creds_service._admin()


def _normalizar(mensaje: str) -> str:
    texto = (mensaje or "")[:500]
    for patron in _VOLATIL:
        texto = patron.sub("·", texto)
    return texto.strip()


def firmar(tipo: str, mensaje: str, nodo: str) -> str:
    crudo = f"{tipo}|{_normalizar(mensaje)}|{nodo}"
    return hashlib.sha1(crudo.encode("utf-8")).hexdigest()[:16]


def _telegram(texto: str) -> bool:
    from ..services import credentials as creds_service

    token = creds_service.get("TELEGRAM_BOT_TOKEN", settings.TELEGRAM_BOT_TOKEN) or ""
    chat_id = (
        settings.ALERT_TELEGRAM_CHAT_ID
        or creds_service.get("GABI_TELEGRAM_CHAT_ID", settings.GABI_TELEGRAM_CHAT_ID)
        or ""
    )
    if not (token and chat_id):
        log.warning("alerta sin destino (falta TELEGRAM_BOT_TOKEN o chat id)")
        return False
    try:
        r = httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": texto[:3900], "disable_web_page_preview": True},
            timeout=15,
        )
        return r.status_code < 300
    except Exception as e:  # noqa: BLE001
        log.warning("no se pudo enviar la alerta: %s", e)
        return False


def _puede_enviar(firma: str) -> bool:
    """True si pasó la ventana desde el último aviso de esta firma. Ante duda, envía."""
    sb = _sb()
    if sb is None:
        return True
    ahora = datetime.now(timezone.utc)
    corte = ahora - timedelta(seconds=settings.SONNER_ALERT_WINDOW_SECONDS)
    try:
        res = (
            sb.table("agent_alerts").select("ultimo_envio, enviados")
            .eq("firma", firma).maybe_single().execute()
        )
        fila = res.data if res else None
        if fila and fila.get("ultimo_envio"):
            ultimo = datetime.fromisoformat(str(fila["ultimo_envio"]).replace("Z", "+00:00"))
            if ultimo > corte:
                return False
        enviados = int((fila or {}).get("enviados") or 0) + 1
        sb.table("agent_alerts").upsert({
            "firma": firma, "ultimo_envio": ahora.isoformat(), "enviados": enviados,
        }).execute()
    except Exception as e:  # noqa: BLE001
        log.warning("rate-limit de alertas no disponible (%s) — envío igual", e)
    return True


def reportar(
    e: BaseException,
    *,
    nodo: str,
    run_id: str | None = None,
    contexto: dict[str, Any] | None = None,
) -> str:
    """Registra el error y avisa por Telegram si pasó la ventana. Devuelve la firma."""
    tipo = type(e).__name__
    mensaje = str(e)
    firma = firmar(tipo, mensaje, nodo)
    log.error("error en %s [%s]: %s", nodo, firma, mensaje,
              extra={"firma": firma, "nodo": nodo, **(contexto or {})})

    cantidad = 1
    sb = _sb()
    if sb is not None:
        try:
            res = sb.rpc("agent_error_registrar", {
                "p_firma": firma, "p_tipo": tipo, "p_mensaje": mensaje[:500],
                "p_nodo": nodo, "p_run_id": run_id,
            }).execute()
            if isinstance(res.data, int):
                cantidad = res.data
        except Exception as err:  # noqa: BLE001
            log.warning("no se pudo registrar el error %s: %s", firma, err)

    if settings.SONNER_ALERT_ENABLED and _puede_enviar(firma):
        _telegram(
            f"🚨 SONNER — error en `{nodo}`\n\n"
            f"{tipo}: {mensaje[:600]}\n\n"
            f"Firma: {firma} · ocurrencias: {cantidad}\n"
            + (f"Run: {run_id}" if run_id else "")
        )
    return firma


def notificar(titulo: str, cuerpo: str, *, clave: str | None = None) -> bool:
    """Alerta que no viene de una excepción (watchdog, umbrales, digest)."""
    if not settings.SONNER_ALERT_ENABLED:
        return False
    firma = clave or hashlib.sha1(titulo.encode("utf-8")).hexdigest()[:16]
    if not _puede_enviar(firma):
        return False
    return _telegram(f"⚠️ SONNER — {titulo}\n\n{cuerpo}")
