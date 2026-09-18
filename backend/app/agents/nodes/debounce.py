"""Nodo `debounce`: agrupa los mensajes que el cliente manda seguidos.

Replica el patrón Redis + Wait de n8n: cada mensaje se empuja a una lista por chat y se
espera la ventana; al despertar, solo sigue el que resultó ser el ÚLTIMO, concatenando
todo lo que llegó mientras tanto. Los demás cortan sin responder.

Con Redis funciona entre workers. Sin Redis hay una variante en memoria con la misma
semántica, válida para un solo proceso — que es la limitación que hoy obliga a correr
`--workers 1`.

El nodo bloquea el hilo durante la ventana: el grafo se invoca desde un thread aparte
(ver `graphs/externo.py`), nunca desde el event loop.
"""
from __future__ import annotations

import logging
import threading
import time

from ...config import settings
from ...obs import runs
from ..state import SonnerState
from . import _redis

log = logging.getLogger("agents.nodes.debounce")

_TTL = 300  # los buffers no deberían sobrevivir más que unas pocas ventanas

# Variante en memoria: clave -> {"mensajes": [...], "token": int}
_memoria: dict[str, dict] = {}
_memoria_lock = threading.Lock()


def _clave(state: SonnerState) -> str:
    return f"{state.get('canal')}:{state.get('chat_id')}"


def _redis_debounce(r, clave: str, texto: str, ventana: float) -> str | None:
    buf = f"sonner:buf:{clave}"
    tok = f"sonner:tok:{clave}"
    pipe = r.pipeline()
    pipe.rpush(buf, texto)
    pipe.expire(buf, _TTL)
    pipe.incr(tok)
    pipe.expire(tok, _TTL)
    mi_token = pipe.execute()[2]

    time.sleep(ventana)

    if str(r.get(tok) or "") != str(mi_token):
        return None  # llegó otro mensaje después: que responda ese
    mensajes = r.lrange(buf, 0, -1)
    r.delete(buf, tok)
    return "\n".join(m for m in mensajes if m).strip()


def _memoria_debounce(clave: str, texto: str, ventana: float) -> str | None:
    with _memoria_lock:
        st = _memoria.setdefault(clave, {"mensajes": [], "token": 0})
        st["mensajes"].append(texto)
        st["token"] += 1
        mi_token = st["token"]

    time.sleep(ventana)

    with _memoria_lock:
        st = _memoria.get(clave)
        if st is None or st["token"] != mi_token:
            return None
        _memoria.pop(clave, None)
        return "\n".join(m for m in st["mensajes"] if m).strip()


def debounce(state: SonnerState) -> dict:
    texto = state.get("mensaje_actual") or ""
    if not texto:
        return {"motivo_corte": "sin_texto"}

    ventana = float(settings.WA_BUFFER_SECONDS)
    clave = _clave(state)

    with runs.paso("debounce", args={"ventana_s": ventana}):
        r = _redis.cliente()
        try:
            agrupado = (
                _redis_debounce(r, clave, texto, ventana) if r is not None
                else _memoria_debounce(clave, texto, ventana)
            )
        except Exception as e:  # noqa: BLE001
            # Un fallo de Redis no puede dejar al cliente sin respuesta: seguimos con
            # el mensaje suelto, que es peor UX que agrupar pero mejor que el silencio.
            log.error("debounce falló (%s) — sigo con el mensaje sin agrupar", e)
            return {}

    if agrupado is None:
        log.info("descarto %s: llegó un mensaje más nuevo", clave)
        return {"motivo_corte": "debounce"}
    return {"mensaje_actual": agrupado}
