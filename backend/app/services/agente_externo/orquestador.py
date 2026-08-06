"""Orquestador del agente externo Tomi (v3.5).

Junta: historial (external_chat_histories) + prompt v3.5 + motor LLM (Claude→OpenAI) +
herramientas + parseo del contrato de salida {respuesta, comando, mensaje_comando}.

NO maneja el canal (YCloud) ni el post-proceso (trocear/Gabi/CRM/CSM): eso va en capas
aparte. Esta función es el "cerebro" puro y testeable por texto.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from ..agente_core import responder as motor_responder, extraer_json
from ..agente import historial as hist
from . import prompt as prompt_mod
from .herramientas import construir_herramientas

log = logging.getLogger("agente_externo.orquestador")

# Si el LLM falla del todo (los 2 proveedores + reintentos) o no devuelve nada usable,
# NUNCA le mandamos un error técnico al cliente: derivamos a Gabriel con un mensaje natural
# (indistinguible de las derivaciones normales) para que un humano tome la conversación.
_HANDOFF = {
    "respuesta": ("¡Gracias por tu mensaje! 🙌 Dame un momento que le paso tu consulta a "
                  "Gabriel y en breve se comunica con vos con todos los detalles."),
    "comando": "mensaje_gabi",
    "mensaje_comando": None,
}

_COMANDOS_VALIDOS = ("mensaje_gabi", "nada")


def _normalizar_contrato(obj: dict[str, Any]) -> dict[str, Any]:
    respuesta = str(obj.get("respuesta") or "").strip()
    comando = str(obj.get("comando") or "nada").strip()
    if comando not in _COMANDOS_VALIDOS:
        comando = "nada"
    mc = obj.get("mensaje_comando", None)
    if isinstance(mc, str) and mc.strip().lower() in ("", "null", "none"):
        mc = None
    if comando == "nada":
        mc = None
    return {"respuesta": respuesta, "comando": comando, "mensaje_comando": mc}


def responder(
    *,
    texto: str,
    telefono: str,
    nombre: str = "",
    tipo_cliente: str = "minorista",
    reunion_cliente: Optional[dict[str, Any]] = None,
    persistir: bool = False,
) -> dict[str, Any]:
    """Corre el cerebro del agente y devuelve {respuesta, comando, mensaje_comando, _meta}.

    - `texto`: mensaje del cliente (ya concatenado si venían varios por el buffer).
    - `persistir`: si True, guarda el turno en external_chat_histories (para producción).
                   En pruebas conviene False para no ensuciar el historial real.
    """
    nombre = nombre or telefono
    historial = hist.cargar(telefono, tabla=hist.TABLE_EXTERNO)

    system = prompt_mod.construir_system(reunion_cliente=reunion_cliente)
    mensaje = prompt_mod.construir_mensaje(texto, nombre, tipo_cliente)

    contrato: Optional[dict[str, Any]] = None
    meta: dict[str, Any] = {}
    try:
        out = motor_responder(
            system=system,
            mensaje=mensaje,
            historial=historial,
            herramientas=construir_herramientas(),
            max_iter=6,
            max_tool_calls=8,
            max_tokens=1200,
        )
        meta = out.get("_meta", {})
        crudo = (out.get("texto") or "").strip()
        obj = extraer_json(crudo)
        if obj:
            contrato = _normalizar_contrato(obj)
        elif crudo and "{" not in crudo and "}" not in crudo:
            # El LLM contestó en prosa (se olvidó del envoltorio JSON): usamos el texto
            # tal cual como respuesta en vez de tirarlo. Es una respuesta válida al cliente.
            contrato = {"respuesta": crudo, "comando": "nada", "mensaje_comando": None}
            meta["parse_prosa"] = True
        else:
            meta["parse_error"] = True
    except Exception as e:  # noqa: BLE001
        log.warning("orquestador externo falló: %s", e)
        meta = {"error": str(e)}

    # Red de seguridad: si no hay un contrato con respuesta útil, derivamos a Gabriel.
    # El cliente jamás recibe un error técnico; se registra en _meta para diagnóstico.
    if not contrato or not contrato.get("respuesta"):
        lead = nombre if nombre and nombre != telefono else ""
        contrato = dict(_HANDOFF)
        contrato["mensaje_comando"] = lead or None
        meta["degradado_handoff"] = True
        log.warning("orquestador externo degradado a handoff (tel=%s meta=%s)", telefono, meta)

    if persistir and contrato["respuesta"]:
        hist.guardar_usuario(telefono, texto, nombre, tabla=hist.TABLE_EXTERNO)
        hist.guardar_agente(telefono, contrato["respuesta"], tabla=hist.TABLE_EXTERNO)

    contrato["_meta"] = meta
    return contrato
