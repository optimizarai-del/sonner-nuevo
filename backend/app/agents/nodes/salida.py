"""Nodo `salida`: manda los fragmentos al cliente con pausa entre mensajes.

Solo corre en modo directo. En modo relay envía n8n, que es el camino de producción hoy.
"""
from __future__ import annotations

import logging
import time

from ...obs import runs
from ...services.agente_externo import canal_ycloud
from ..state import SonnerState

log = logging.getLogger("agents.nodes.salida")

PAUSA_SEGUNDOS = 2.0


def salida(state: SonnerState) -> dict:
    fragmentos = state.get("fragmentos") or []
    if not fragmentos:
        return {}
    inbound = state.get("inbound") or {}
    meta = dict(state.get("meta") or {})

    with runs.paso("salida", args={"fragmentos": len(fragmentos)}):
        enviados = 0
        for i, fragmento in enumerate(fragmentos):
            if canal_ycloud.enviar(inbound.get("usuario"), inbound.get("nosotros"), fragmento):
                enviados += 1
            if i < len(fragmentos) - 1:
                time.sleep(PAUSA_SEGUNDOS)

    if enviados < len(fragmentos):
        log.warning("se enviaron %d de %d fragmentos", enviados, len(fragmentos))
    meta["enviados"] = enviados
    return {"meta": meta}
