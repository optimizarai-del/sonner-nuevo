"""Grafo del agente externo (Tomi / cliente final).

Dos recorridos sobre el mismo grafo, según `modo`:

  directo  START → ingesta → gate → debounce → contexto → agente ⇄ herramientas
                 → guard → persistencia → troceo → salida → efectos → END
  relay    START ─────────────────────────────→ contexto → agente ⇄ herramientas
                 → guard → persistencia → END

`relay` es el camino de producción hoy: n8n recibe, agrupa, envía y registra; el grafo
solo piensa. `directo` es el camino completo, para cuando el webhook apunte acá.

El grafo es **síncrono a propósito**. El debounce duerme y las consultas a Supabase son
bloqueantes; correrlo en el event loop lo trabaría. Los transportes lo invocan desde un
thread aparte.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from langgraph.graph import END, START, StateGraph

from ...obs import alertas, runs
from ..nodes.agente import agente, seguir
from ..nodes.contexto import contexto
from ..nodes.debounce import debounce
from ..nodes.efectos import efectos, persistencia
from ..nodes.gate import gate
from ..nodes.guard import HANDOFF_RESPUESTA, guard
from ..nodes.herramientas import herramientas
from ..nodes.ingesta import ingesta
from ..nodes.salida import salida
from ..nodes.troceo import troceo
from ..state import SonnerState, nuevo

log = logging.getLogger("agents.graphs.externo")


def _entrada(state: SonnerState) -> str:
    return "contexto" if state.get("modo") == "relay" else "ingesta"


def _cortado(siguiente: str):
    """Después de un nodo que puede cortar: END si cortó, `siguiente` si no."""

    def _ruta(state: SonnerState) -> str:
        return END if state.get("motivo_corte") else siguiente

    return _ruta


def _despues_de_persistir(state: SonnerState) -> str:
    return END if state.get("modo") == "relay" else "troceo"


@lru_cache(maxsize=1)
def compilado():
    g = StateGraph(SonnerState)

    g.add_node("ingesta", ingesta)
    g.add_node("gate", gate)
    g.add_node("debounce", debounce)
    g.add_node("contexto", contexto)
    g.add_node("agente", agente)
    g.add_node("herramientas", herramientas)
    g.add_node("guard", guard)
    g.add_node("persistencia", persistencia)
    g.add_node("troceo", troceo)
    g.add_node("salida", salida)
    g.add_node("efectos", efectos)

    g.add_conditional_edges(START, _entrada, {"ingesta": "ingesta", "contexto": "contexto"})
    g.add_conditional_edges("ingesta", _cortado("gate"), {END: END, "gate": "gate"})
    g.add_conditional_edges("gate", _cortado("debounce"), {END: END, "debounce": "debounce"})
    g.add_conditional_edges("debounce", _cortado("contexto"), {END: END, "contexto": "contexto"})
    g.add_edge("contexto", "agente")
    g.add_conditional_edges("agente", seguir,
                            {"herramientas": "herramientas", "guard": "guard"})
    g.add_edge("herramientas", "agente")
    g.add_edge("guard", "persistencia")
    g.add_conditional_edges("persistencia", _despues_de_persistir, {END: END, "troceo": "troceo"})
    g.add_edge("troceo", "salida")
    g.add_edge("salida", "efectos")
    g.add_edge("efectos", END)

    return g.compile()


# ── API pública ──────────────────────────────────────────────────────────────
def correr(
    *,
    modo: str,
    chat_id: str,
    canal: str = "whatsapp",
    mensaje: str = "",
    nombre: str = "",
    inbound: dict[str, Any] | None = None,
    tipo_cliente: str | None = None,
    reunion: dict[str, Any] | None = None,
    persistir: bool = True,
) -> dict[str, Any]:
    """Corre el grafo y devuelve el contrato {respuesta, comando, mensaje_comando, _meta}.

    Nunca lanza: si el grafo explota, degrada a derivación humana. El cliente no puede
    quedarse sin respuesta porque se nos cayó algo.
    """
    run = runs.iniciar(
        canal=canal, audiencia="externo", chat_id=chat_id,
        entrada=mensaje or str((inbound or {}).get("texto") or ""), nombre=nombre,
    )
    estado = nuevo(
        run_id=run.run_id, canal=canal, audiencia="externo", chat_id=chat_id,  # type: ignore[arg-type]
        modo=modo, inbound=inbound, nombre=nombre, mensaje_actual=mensaje,  # type: ignore[arg-type]
        tipo_cliente=tipo_cliente, reunion=reunion, persistir=persistir,
    )

    with runs.activa(run):
        try:
            final = compilado().invoke(estado)
        except Exception as e:  # noqa: BLE001
            alertas.reportar(e, nodo="grafo", run_id=run.run_id, contexto={"chat_id": chat_id})
            run.cerrar(respuesta=HANDOFF_RESPUESTA, comando="mensaje_gabi",
                       degradado=True, ok=False,
                       meta={"error": str(e), "motivo_handoff": "excepcion_grafo"})
            return {
                "respuesta": HANDOFF_RESPUESTA, "comando": "mensaje_gabi",
                "mensaje_comando": nombre or None,
                "_meta": {"degradado_handoff": True, "error": str(e)},
            }

        if final.get("motivo_corte"):
            run.cortar(final["motivo_corte"])
            return {
                "respuesta": "", "comando": "nada", "mensaje_comando": None,
                "_meta": {"cortado": final["motivo_corte"]},
            }

        meta = final.get("meta") or {}
        run.cerrar(
            respuesta=final.get("respuesta"), comando=final.get("comando"),
            mensaje_comando=final.get("mensaje_comando"),
            degradado=bool(final.get("degradado")), ok=True, meta=meta,
        )
        return {
            "respuesta": final.get("respuesta") or "",
            "comando": final.get("comando") or "nada",
            "mensaje_comando": final.get("mensaje_comando"),
            "tipo_cliente": final.get("tipo_cliente"),
            "_meta": {**meta, "degradado_handoff": bool(final.get("degradado"))},
        }


def correr_en_background(inbound: dict[str, Any]) -> None:
    """Lanza el recorrido directo en un thread para devolver el webhook al instante.

    El grafo es bloqueante (el debounce duerme la ventana entera); si corriera en el
    event loop, un mensaje trabaría a todos los demás.
    """
    import threading

    def _tarea() -> None:
        try:
            correr(
                modo="directo",
                canal="whatsapp",
                chat_id=str(inbound.get("usuario") or ""),
                nombre=str(inbound.get("nombre") or ""),
                inbound=inbound,
            )
        except Exception as e:  # noqa: BLE001
            log.exception("el grafo en background murió: %s", e)

    threading.Thread(target=_tarea, daemon=True).start()
