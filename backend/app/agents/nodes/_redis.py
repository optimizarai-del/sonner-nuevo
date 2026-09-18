"""Cliente Redis compartido por los nodos que necesitan estado entre workers.

Redis es opcional. Si `REDIS_URL` no está configurada, `cliente()` devuelve None y los
nodos caen a su variante en memoria — que funciona, pero obliga a correr con UN worker
(cada proceso tendría su propio buffer y su propio registro de duplicados).
"""
from __future__ import annotations

import logging
import threading
from typing import Any

from ...config import settings

log = logging.getLogger("agents.redis")

_cliente: Any = None
_probado = False
_lock = threading.Lock()


def cliente() -> Any:
    """Cliente Redis listo, o None. Se conecta una sola vez por proceso."""
    global _cliente, _probado
    if _probado:
        return _cliente
    with _lock:
        if _probado:
            return _cliente
        _probado = True
        if not settings.REDIS_URL:
            log.warning(
                "REDIS_URL sin configurar — debounce y dedupe en memoria. "
                "El servicio tiene que correr con --workers 1."
            )
            return None
        try:
            import redis

            c = redis.Redis.from_url(
                settings.REDIS_URL, decode_responses=True,
                socket_timeout=5, socket_connect_timeout=5,
            )
            c.ping()
            _cliente = c
            log.info("Redis conectado — debounce distribuido activo")
        except Exception as e:  # noqa: BLE001
            log.error("no se pudo conectar a Redis (%s) — sigo en memoria", e)
            _cliente = None
    return _cliente
