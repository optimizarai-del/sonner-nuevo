"""Nodo `herramientas`: ejecuta las tools que pidió el agente.

Se escribe a mano en vez de usar el `ToolNode` de langgraph.prebuilt porque cada
ejecución tiene que quedar en `agent_steps` con sus argumentos, su duración y su error
—que es la mitad de poder diagnosticar una conversación sin abrir los logs.

Una tool nunca lanza hacia afuera: el error vuelve como `{"error": ...}` para que el
modelo lo vea y decida (pedir otra cosa, derivar a Gabriel), igual que hacía
`Herramienta.correr()`.
"""
from __future__ import annotations

import json
import logging
import time

from langchain_core.messages import AIMessage, ToolMessage

from ...obs import runs
from ..state import SonnerState
from ..tools import registry

log = logging.getLogger("agents.nodes.herramientas")


def _serializar(salida: object) -> str:
    if isinstance(salida, str):
        return salida
    try:
        return json.dumps(salida, ensure_ascii=False, default=str)
    except Exception:  # noqa: BLE001
        return str(salida)


def herramientas(state: SonnerState) -> dict:
    mensajes = state.get("messages") or []
    ultimo = mensajes[-1] if mensajes else None
    if not isinstance(ultimo, AIMessage) or not ultimo.tool_calls:
        return {}

    disponibles = registry.por_nombre(state.get("audiencia") or "externo")
    run = runs.actual()
    salidas: list[ToolMessage] = []

    for llamada in ultimo.tool_calls:
        nombre = llamada.get("name") or ""
        args = llamada.get("args") or {}
        inicio = time.monotonic()
        error: str | None = None

        tool = disponibles.get(nombre)
        if tool is None:
            # Puede pasar si el modelo alucina una tool de otra audiencia. No es un
            # error del sistema: se lo decimos al modelo y sigue.
            resultado: object = {"error": f"tool no disponible: {nombre}"}
            error = "tool_no_disponible"
            log.warning("el modelo pidió una tool fuera de su alcance: %s", nombre)
        else:
            try:
                resultado = tool.invoke(args)
            except Exception as e:  # noqa: BLE001
                resultado = {"error": str(e)}
                error = f"{type(e).__name__}: {e}"
                log.warning("tool %s falló: %s", nombre, e)

        duracion = int((time.monotonic() - inicio) * 1000)
        if run is not None:
            run.registrar_tool(nombre, args, _serializar(resultado), duracion, error)

        salidas.append(ToolMessage(
            content=_serializar(resultado), tool_call_id=llamada.get("id") or "", name=nombre,
        ))

    return {"messages": salidas}
