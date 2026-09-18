"""Grafo del agente interno (equipo de SONNER: Telegram y chat de la plataforma).

Los dos workflows internos de n8n —`AGT-INTERNO-SONNER` (Telegram, 63 nodos) y
`AGT-INTERNO-SONNER PAGINA` (web, 61 nodos)— eran el mismo agente duplicado: cambiaba
el trigger y cómo se devolvía la respuesta, nada más. Acá es **un grafo y dos canales**;
`canal` solo afecta el troceo (Telegram corta en 4 mensajes, la web responde de una).

    START → contexto → agente ⇄ herramientas → guard → persistencia
          → ingesta_vectorial → troceo → END

No hay `salida`: el envío lo hace n8n en los dos canales (Telegram con su credencial,
la web respondiendo el webhook). Tampoco hay `gate` ni `debounce`: de este lado está el
equipo, no hay kill-switch ni blocklist que aplicar, y el debounce sigue en n8n.

Lo que NO se portó, a propósito: el hack anti-loop del workflow (detectar
`json|temperatura|comando|ejecutado` en la salida y reintentar hasta 2 veces guardando
el contador en `$getWorkflowStaticData`). Ese parche existía porque el output parser de
n8n a veces filtraba JSON crudo al chat. Con el contrato de Pydantic en `guard` eso no
puede pasar, y si pasara lo atrapa `guard`, no un regex sobre el texto final.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from langgraph.graph import END, START, StateGraph

from ...obs import alertas, runs
from ..nodes.agente import agente, seguir
from ..nodes.contexto import contexto
from ..nodes.efectos import persistencia
from ..nodes.guard import FALLA_INTERNA, guard
from ..nodes.herramientas import herramientas
from ..nodes.ingesta_vectorial import ingesta_vectorial
from ..nodes.troceo import troceo
from ..state import SonnerState, nuevo

log = logging.getLogger("agents.graphs.interno")


@lru_cache(maxsize=1)
def compilado():
    g = StateGraph(SonnerState)

    g.add_node("contexto", contexto)
    g.add_node("agente", agente)
    g.add_node("herramientas", herramientas)
    g.add_node("guard", guard)
    g.add_node("persistencia", persistencia)
    g.add_node("ingesta_vectorial", ingesta_vectorial)
    g.add_node("troceo", troceo)

    g.add_edge(START, "contexto")
    g.add_edge("contexto", "agente")
    g.add_conditional_edges("agente", seguir,
                            {"herramientas": "herramientas", "guard": "guard"})
    g.add_edge("herramientas", "agente")
    g.add_edge("guard", "persistencia")
    g.add_edge("persistencia", "ingesta_vectorial")
    g.add_edge("ingesta_vectorial", "troceo")
    g.add_edge("troceo", END)

    return g.compile()


def correr(
    *,
    chat_id: str,
    mensaje: str,
    canal: str = "telegram",
    nombre: str = "",
    persistir: bool = True,
) -> dict[str, Any]:
    """Corre el agente interno. Devuelve {respuesta, comando, contenido, fragmentos, _meta}.

    Nunca lanza: si el grafo explota, devuelve el aviso de falla. Al equipo sí se le
    dice que algo se rompió —son quienes pueden arreglarlo— y sobre todo se les aclara
    que no se ejecutó ningún cambio, para que no asuman que la acción salió.
    """
    run = runs.iniciar(canal=canal, audiencia="interno", chat_id=chat_id,
                       entrada=mensaje, nombre=nombre)
    estado = nuevo(
        run_id=run.run_id, canal=canal, audiencia="interno",  # type: ignore[arg-type]
        chat_id=chat_id, modo="relay", nombre=nombre,
        mensaje_actual=mensaje, persistir=persistir,
    )

    with runs.activa(run):
        try:
            final = compilado().invoke(estado)
        except Exception as e:  # noqa: BLE001
            alertas.reportar(e, nodo="grafo_interno", run_id=run.run_id,
                             contexto={"chat_id": chat_id})
            run.cerrar(respuesta=FALLA_INTERNA, degradado=True, ok=False,
                       meta={"error": str(e), "motivo_handoff": "excepcion_grafo"})
            return {"respuesta": FALLA_INTERNA, "comando": "nada", "contenido": None,
                    "fragmentos": [FALLA_INTERNA],
                    "_meta": {"degradado_handoff": True, "error": str(e)}}

        meta = final.get("meta") or {}
        run.cerrar(respuesta=final.get("respuesta"), comando=final.get("comando"),
                   mensaje_comando=final.get("contenido"),
                   degradado=bool(final.get("degradado")), ok=True, meta=meta)
        return {
            "respuesta": final.get("respuesta") or "",
            "comando": final.get("comando") or "nada",
            "contenido": final.get("contenido"),
            "fragmentos": final.get("fragmentos") or [],
            "_meta": {**meta, "degradado_handoff": bool(final.get("degradado"))},
        }
