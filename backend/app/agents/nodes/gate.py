"""Nodo `gate`: kill-switch, blocklist y deduplicación por id de mensaje.

Los dos primeros replican los nodos `Check automatización` y `blocklist` de n8n. El
tercero es nuevo: YCloud reintenta el webhook si no contestamos rápido, y sin dedupe un
reintento se procesa como un mensaje más (el cliente recibe la respuesta dos veces).
"""
from __future__ import annotations

import logging
import threading
import time

from ...obs import runs
from ...services.agente_externo import supabase_ops
from ..state import SonnerState
from . import _redis

log = logging.getLogger("agents.nodes.gate")

# Ventana de dedupe: solo tiene que cubrir los reintentos de YCloud (segundos), no es
# un registro histórico.
_VISTOS_TTL = 300
_VISTOS: dict[str, float] = {}
_VISTOS_LOCK = threading.Lock()


def _ya_visto(message_id: str) -> bool:
    """True si este id ya se procesó. Con Redis vale entre workers; sin él, por proceso."""
    if not message_id:
        return False
    r = _redis.cliente()
    if r is not None:
        try:
            # SET NX: gana el primero que llega, los demás ven que ya existe.
            return not bool(r.set(f"sonner:visto:{message_id}", "1", nx=True, ex=_VISTOS_TTL))
        except Exception as e:  # noqa: BLE001
            log.warning("dedupe por Redis falló (%s) — uso memoria", e)

    ahora = time.monotonic()
    with _VISTOS_LOCK:
        for k, exp in list(_VISTOS.items()):
            if exp < ahora:
                _VISTOS.pop(k, None)
        if message_id in _VISTOS:
            return True
        _VISTOS[message_id] = ahora + _VISTOS_TTL
    return False


def gate(state: SonnerState) -> dict:
    chat_id = state.get("chat_id") or ""
    inbound = state.get("inbound") or {}

    with runs.paso("gate"):
        message_id = str(inbound.get("message_id") or inbound.get("id") or "")
        if _ya_visto(message_id):
            log.info("mensaje %s ya procesado — ignoro el reintento", message_id)
            return {"motivo_corte": "duplicado"}

        if not supabase_ops.automatizacion_activa():
            log.info("automatización OFF — ignoro mensaje de %s", chat_id)
            return {"motivo_corte": "kill_switch"}

        if supabase_ops.esta_bloqueado(chat_id):
            log.info("contacto bloqueado %s — ignoro", chat_id)
            return {"motivo_corte": "blocklist"}

    return {}
