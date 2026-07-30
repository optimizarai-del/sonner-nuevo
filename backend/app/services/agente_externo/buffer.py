"""Buffer/debounce de mensajes entrantes por contacto (en memoria).

Reemplaza el patrón Redis+Wait de n8n: el cliente suele mandar varios mensajes seguidos;
esperamos `delay` segundos, los concatenamos y recién ahí procesamos UNA vez. Si llega un
mensaje nuevo mientras esperamos, se reinicia la espera (solo corre el último timer).

En memoria = válido para un solo proceso/worker (el caso de EasyPanel). Para multi-worker
habría que mover esto a Redis. Best-effort: si algo falla, no rompe el webhook.
"""
from __future__ import annotations

import logging
import threading
from typing import Any, Callable

log = logging.getLogger("agente_externo.buffer")

_lock = threading.Lock()
# clave(tel) -> {"mensajes": [str], "meta": dict, "token": int, "timer": Timer}
_estado: dict[str, dict[str, Any]] = {}


def encolar(
    clave: str,
    texto: str,
    meta: dict[str, Any],
    callback: Callable[[str, str, dict[str, Any]], None],
    delay: float,
) -> None:
    """Agrega `texto` al buffer de `clave` y (re)programa el disparo del callback.

    Al disparar (si nadie encoló algo nuevo), llama callback(clave, texto_concatenado, meta).
    """
    with _lock:
        st = _estado.get(clave)
        if st is None:
            st = {"mensajes": [], "meta": meta, "token": 0, "timer": None}
            _estado[clave] = st
        if texto:
            st["mensajes"].append(texto)
        st["meta"] = meta  # el último inbound gana (nombre/nosotros más recientes)
        st["token"] += 1
        token = st["token"]
        if st["timer"] is not None:
            st["timer"].cancel()
        timer = threading.Timer(delay, _disparar, args=(clave, token, callback))
        timer.daemon = True
        st["timer"] = timer
        timer.start()


def _disparar(clave: str, token: int, callback: Callable[[str, str, dict[str, Any]], None]) -> None:
    with _lock:
        st = _estado.get(clave)
        if st is None or st["token"] != token:
            return  # llegó un mensaje más nuevo → este disparo quedó obsoleto
        mensajes = st["mensajes"]
        meta = st["meta"]
        _estado.pop(clave, None)
    texto = "\n".join(m for m in mensajes if m).strip()
    if not texto:
        return
    try:
        callback(clave, texto, meta)
    except Exception as e:  # noqa: BLE001
        log.exception("callback del buffer falló para %s: %s", clave, e)
