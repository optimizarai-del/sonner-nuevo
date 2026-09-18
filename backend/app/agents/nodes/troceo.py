"""Nodo `troceo`: parte la respuesta en mensajes cortos, como el Code de n8n.

Un párrafo por mensaje, con tope de 4. Si no hay párrafos se corta por frases. Si quedan
más bloques que el tope, se agrupan. Es lo que hace que la conversación se lea como
WhatsApp y no como un mail.
"""
from __future__ import annotations

from ...obs import runs
from ...services.agente_externo import post
from ..state import SonnerState

MAXIMO_POR_CANAL = {"whatsapp": 4, "telegram": 4, "web": 1}


def troceo(state: SonnerState) -> dict:
    respuesta = state.get("respuesta") or ""
    maximo = MAXIMO_POR_CANAL.get(state.get("canal") or "whatsapp", 4)

    with runs.paso("troceo"):
        fragmentos = [respuesta.strip()] if maximo == 1 and respuesta.strip() else post.trocear(
            respuesta, maximo=maximo
        )

    return {"fragmentos": fragmentos}
