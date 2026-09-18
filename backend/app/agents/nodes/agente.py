"""Nodo `agente`: la única llamada a LLM del grafo.

Reemplaza al nodo AI Agent de n8n. El modelo se arma con las tools de la audiencia y con
fallback de proveedor (Claude → OpenAI). El control del loop vive en `seguir()`: topes
duros de iteraciones y de tool calls, para que un modelo que se queda pidiendo tools no
se lleve puesto el presupuesto ni deje al cliente esperando.
"""
from __future__ import annotations

import logging
from functools import lru_cache

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage

from ...config import settings
from ...obs import runs
from .. import llm
from ..state import SonnerState
from ..tools import registry

log = logging.getLogger("agents.nodes.agente")

_MAX_TOKENS = 1200


@lru_cache(maxsize=4)
def _modelo(audiencia: str) -> BaseChatModel:
    return llm.construir(registry.para(audiencia), max_tokens=_MAX_TOKENS)


def agente(state: SonnerState) -> dict:
    audiencia = state.get("audiencia") or "externo"
    meta = dict(state.get("meta") or {})

    with runs.paso("agente", args={"iteracion": meta.get("iteraciones", 0) + 1}):
        respuesta = _modelo(audiencia).invoke(state["messages"])

    meta["iteraciones"] = meta.get("iteraciones", 0) + 1
    if isinstance(respuesta, AIMessage):
        meta.update(llm.leer_uso(respuesta))
        meta["tool_calls"] = meta.get("tool_calls", 0) + len(respuesta.tool_calls or [])

    return {"messages": [respuesta], "meta": meta}


def seguir(state: SonnerState) -> str:
    """Decide si hay que ejecutar tools o ya se puede parsear la respuesta."""
    mensajes = state.get("messages") or []
    ultimo = mensajes[-1] if mensajes else None
    if not isinstance(ultimo, AIMessage) or not ultimo.tool_calls:
        return "guard"

    meta = state.get("meta") or {}
    if meta.get("iteraciones", 0) >= settings.SONNER_MAX_ITER:
        log.warning("tope de iteraciones (%d) alcanzado", settings.SONNER_MAX_ITER)
        return "guard"
    if meta.get("tool_calls", 0) > settings.SONNER_MAX_TOOL_CALLS:
        log.warning("tope de tool calls (%d) alcanzado", settings.SONNER_MAX_TOOL_CALLS)
        return "guard"
    return "herramientas"
