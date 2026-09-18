"""Nodos de efectos laterales: persistir el turno, avisar a Gabi, CRM y CSM.

Dos nodos distintos porque corren en momentos distintos:

- `persistencia` — guarda el turno en `external_chat_histories`. Corre SIEMPRE, también
  en modo relay: si no, el agente pierde el hilo de la conversación.
- `efectos` — aviso a Gabi, CRM y CSM. Solo en modo directo; en relay esas ramas siguen
  en n8n y duplicarlas generaría leads y filas de CRM repetidas.

Todo best-effort: la respuesta al cliente ya salió, ninguno de estos puede hacerla fallar.
"""
from __future__ import annotations

import logging

from ...obs import alertas, runs
from ...services.agente import historial as hist
from ...services.agente_externo import post
from ..state import SonnerState
from .contexto import TABLA_POR_AUDIENCIA

log = logging.getLogger("agents.nodes.efectos")


def persistencia(state: SonnerState) -> dict:
    chat_id = state.get("chat_id") or ""
    entrada = state.get("mensaje_actual") or ""
    respuesta = state.get("respuesta") or ""
    if not (chat_id and respuesta) or not state.get("persistir", True):
        return {}

    tabla = TABLA_POR_AUDIENCIA[state.get("audiencia") or "externo"]
    with runs.paso("persistencia", args={"tabla": tabla}):
        try:
            hist.guardar_usuario(chat_id, entrada, state.get("nombre") or "", tabla=tabla)
            hist.guardar_agente(chat_id, respuesta, tabla=tabla)
        except Exception as e:  # noqa: BLE001
            # Perder el historial degrada las próximas respuestas: vale una alerta.
            alertas.reportar(e, nodo="persistencia", run_id=state.get("run_id"))
    return {}


def efectos(state: SonnerState) -> dict:
    inbound = state.get("inbound") or {}
    entrada = state.get("mensaje_actual") or ""
    respuesta = state.get("respuesta") or ""

    with runs.paso("efectos"):
        if state.get("comando") == "mensaje_gabi":
            post.avisar_gabi(inbound, state.get("mensaje_comando"))
        post.registrar_crm(inbound, entrada, respuesta)
        post.registrar_csm(inbound, entrada, respuesta, state.get("tipo_cliente") or "minorista")
    return {}
