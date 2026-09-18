"""Nodo `ingesta`: normaliza el mensaje entrante a texto.

Equivale al Switch de n8n por `tipo-contenido-mensaje`: texto pasa derecho, el audio se
transcribe con Whisper, la imagen se describe con visión, y cualquier otro tipo (video,
documento) se ignora — igual que hoy.
"""
from __future__ import annotations

import logging

from ...obs import runs
from ...services.agente_externo import media
from ..state import SonnerState

log = logging.getLogger("agents.nodes.ingesta")


def ingesta(state: SonnerState) -> dict:
    inbound = state.get("inbound") or {}
    tipo = inbound.get("tipo") or "text"

    with runs.paso("ingesta", args={"tipo": tipo}):
        texto = media.a_texto(inbound)
        if texto is None:
            log.info("tipo de mensaje no soportado (%s) — ignoro", tipo)
            return {"motivo_corte": "tipo_no_soportado"}
        texto = texto.strip()
        if not texto:
            return {"motivo_corte": "sin_texto"}
        return {"mensaje_actual": texto}
