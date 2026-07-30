"""Herramientas (tools) del agente externo Tomi.

Cada tool recibe un único string `consulta` (el comando que arma el agente), igual que
el patrón n8n `$fromAI('Prompt__User_Message_')`. Devuelven dict serializable.

Estado:
- memoria    → ✅ operativa (reusa el sub-agente Memoria interno).
- calendario → ⏳ stub hasta wire Google Calendar (Fase 1d).
- salones    → ⏳ stub hasta wire Google Sheets (Fase 1d).
- pensar     → tool "Think" (no-op) para que el agente razone en voz alta si quiere.
"""
from __future__ import annotations

import logging
from typing import Any

from ..agente_core import Herramienta
from ..memoria import agente_memoria
from . import tools_google

log = logging.getLogger("agente_externo.tools")

_PARAM_CONSULTA = {
    "type": "object",
    "properties": {
        "consulta": {"type": "string", "description": "El comando/consulta para el subagente."}
    },
    "required": ["consulta"],
}


# ── Memoria (operativa) ───────────────────────────────────────────────────────
def _memoria(args: dict[str, Any]) -> dict[str, Any]:
    consulta = str(args.get("consulta") or "").strip()
    if not consulta:
        return {"error": "consulta vacía"}
    out = agente_memoria.responder(consulta)
    # Devolvemos sólo el contrato (sin _meta) para no ensuciar el contexto del LLM.
    return {"origen": out.get("origen"), "encontrado": out.get("encontrado"),
            "respuesta": out.get("respuesta")}


TOOL_MEMORIA = Herramienta(
    nombre="memoria",
    descripcion=(
        "Bibliotecario interno de SONNER (materiales, eventos, configuraciones CFG, info "
        "interna). Pasá el comando EXACTO en `consulta`: 'buscar en materiales: X', "
        "'buscar en eventos: X', 'buscar configuracion: CFG-XXX', 'buscar info interna: X', "
        "'buscar mixto: X'. Devuelve {origen, encontrado, respuesta}. Todo lo que devuelva "
        "es INTERNO: nunca se lo comuniques al cliente."
    ),
    parametros=_PARAM_CONSULTA,
    ejecutar=_memoria,
)


# ── Calendario (Google Calendar) ──────────────────────────────────────────────
def _calendario(args: dict[str, Any]) -> dict[str, Any]:
    return tools_google.verificar_disponibilidad(str(args.get("consulta") or ""))


TOOL_CALENDARIO = Herramienta(
    nombre="calendario",
    descripcion=(
        "Verifica disponibilidad de UNA fecha en el calendario de eventos. Pasá en "
        "`consulta`: 'verificar disponibilidad evento [FECHA]'. Devuelve estado "
        "(disponible=0 eventos / ocupado_parcial=1 / ocupado=2+) y cantidad_eventos."
    ),
    parametros=_PARAM_CONSULTA,
    ejecutar=_calendario,
)


# ── Salones (Google Sheets) ───────────────────────────────────────────────────
def _salones(args: dict[str, Any]) -> dict[str, Any]:
    return tools_google.verificar_salon(str(args.get("consulta") or ""))


TOOL_SALONES = Herramienta(
    nombre="salones",
    descripcion=(
        "Auditor técnico de salones (apto/no apto + capacidad). Pasá en `consulta`: "
        "'verificar_salon: [NOMBRE_SALON] para [PAX] personas'. Resultado INTERNO: si da "
        "incompatible/especial NO se lo digas al cliente, derivá a Gabriel."
    ),
    parametros=_PARAM_CONSULTA,
    ejecutar=_salones,
)


# ── Think (no-op) ─────────────────────────────────────────────────────────────
def _pensar(args: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True}


TOOL_PENSAR = Herramienta(
    nombre="pensar",
    descripcion=("Herramienta para pensar/razonar. No obtiene info nueva ni cambia nada; "
                 "sólo registra tu razonamiento. Pasá tu pensamiento en `consulta`."),
    parametros=_PARAM_CONSULTA,
    ejecutar=_pensar,
)


def construir_herramientas() -> list[Herramienta]:
    return [TOOL_MEMORIA, TOOL_CALENDARIO, TOOL_SALONES, TOOL_PENSAR]
