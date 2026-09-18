"""Nodo `ingesta_vectorial`: guarda en el vector store lo que el agente interno decidió.

Reemplaza al Switch de n8n y a sus tres ramas de ingesta (Supabase Vector Store +
Default Data Loader + Recursive Splitter + Embeddings, una por destino).

El comando del contrato interno decide la fuente:
    eventos     → documents(source='eventos')
    informacion → documents(source='informacion_interna')
    materiales  → documents(source='materiales')
    nada        → no se guarda nada

Es escritura, así que falla ruidosamente: si no se pudo guardar, el equipo tiene que
enterarse en la misma respuesta, no descubrirlo dentro de dos semanas cuando busque el
dato y no esté.
"""
from __future__ import annotations

import logging

from ...obs import alertas, runs
from ...services.memoria import vectorstore as vs
from ..state import SonnerState

log = logging.getLogger("agents.nodes.ingesta_vectorial")

# comando del contrato interno → metadata.source en la tabla `documents`
DESTINO = {
    "eventos": "eventos",
    "informacion": "informacion_interna",
    "materiales": "materiales",
}


def ingesta_vectorial(state: SonnerState) -> dict:
    comando = state.get("comando") or "nada"
    contenido = (state.get("contenido") or "").strip()
    fuente = DESTINO.get(comando)
    if not fuente or not contenido:
        return {}

    meta = dict(state.get("meta") or {})
    with runs.paso("ingesta_vectorial", args={"fuente": fuente, "largo": len(contenido)}):
        try:
            resultado = vs.ingestar(contenido, fuente,
                                    metadata={"origen": "agente_interno",
                                              "chat_id": state.get("chat_id")})
            meta["ingesta"] = resultado
        except Exception as e:  # noqa: BLE001
            alertas.reportar(e, nodo="ingesta_vectorial", run_id=state.get("run_id"),
                             contexto={"fuente": fuente})
            meta["ingesta"] = {"guardados": 0, "error": str(e)}
            return {
                "respuesta": (state.get("respuesta") or "")
                + f"\n\n⚠️ No se pudo guardar en la memoria de {fuente}: {e}",
                "meta": meta,
            }
    return {"meta": meta}
