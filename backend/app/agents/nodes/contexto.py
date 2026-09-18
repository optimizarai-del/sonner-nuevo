"""Nodo `contexto`: arma todo lo que el agente necesita saber antes de pensar.

Cada audiencia arma lo suyo:

- **externo**: `tipo_cliente` (RPC `es_mayorista`) y la próxima reunión agendada, si el
  transporte no los precargó, más el prompt v3.5 con la fecha AR y esa reunión.
- **interno**: el prompt del equipo con la fecha real. No hay segmentación ni reunión:
  del otro lado está Gabi, no un cliente.

El historial sale de Supabase vía REST y no del checkpointer de LangGraph a propósito:
durante la transición las dos escrituras conviven (plan §2.4) y n8n todavía puede estar
leyendo esas tablas. Cada audiencia usa la suya, las mismas que escribía n8n.
"""
from __future__ import annotations

import logging

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from ...obs import runs
from ...services.agente import historial as hist
from ...services.agente_externo import prompt as prompt_externo
from ...services.agente_externo import supabase_ops
from ..prompts import loader as prompt_interno
from ..state import SonnerState

log = logging.getLogger("agents.nodes.contexto")

TABLA_POR_AUDIENCIA = {
    "externo": hist.TABLE_EXTERNO,
    "interno": hist.TABLE_INTERNO,
}


def _turnos_previos(mensajes: list[dict[str, str]]) -> list:
    convertidos = []
    for turno in mensajes:
        contenido = turno.get("content") or ""
        if not contenido:
            continue
        convertidos.append(
            HumanMessage(content=contenido) if turno.get("role") == "user"
            else AIMessage(content=contenido)
        )
    return convertidos


def _externo(state: SonnerState, chat_id: str) -> tuple[str, str, dict]:
    tipo = state.get("tipo_cliente") or supabase_ops.tipo_cliente(chat_id)
    reunion = state.get("reunion")
    if reunion is None:
        reunion = supabase_ops.contexto_reunion(chat_id)
    sistema = prompt_externo.construir_system(reunion_cliente=reunion)
    humano = prompt_externo.construir_mensaje(
        state.get("mensaje_actual") or "", state.get("nombre") or chat_id, tipo)
    return sistema, humano, {"tipo_cliente": tipo, "reunion": reunion}


def _interno(state: SonnerState, chat_id: str) -> tuple[str, str, dict]:
    sistema = prompt_interno.interno()
    humano = prompt_interno.mensaje_interno(
        state.get("mensaje_actual") or "", state.get("nombre") or "")
    return sistema, humano, {}


def contexto(state: SonnerState) -> dict:
    audiencia = state.get("audiencia") or "externo"
    chat_id = state.get("chat_id") or ""

    with runs.paso("contexto", args={"audiencia": audiencia}):
        armar = _interno if audiencia == "interno" else _externo
        sistema, humano, extra = armar(state, chat_id)
        previos = hist.cargar(chat_id, tabla=TABLA_POR_AUDIENCIA[audiencia])

    mensajes = [SystemMessage(content=sistema), *_turnos_previos(previos),
                HumanMessage(content=humano)]
    return {**extra, "messages": mensajes}
