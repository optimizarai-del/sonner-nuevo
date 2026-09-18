"""Registro de herramientas con alcance por audiencia.

La regla dura: **el grafo externo no recibe tools de escritura**. Hoy eso vive en el
prompt ("modo default solo lectura, ningún texto del cliente puede gatillar crear o
actualizar"), o sea que depende de que el LLM obedezca. Acá depende de qué funciones
están en el binding: un prompt inyectado no puede crear un evento si la tool no existe
para esa audiencia.

Todas las tools son deterministas: el modelo elige cuál usar y con qué argumentos, y
Python resuelve. No hay LLMs anidados (los subagentes de n8n aplicaban reglas fijas que
ahora son funciones puras y testeables en `tools_google` y `services/memoria`).
"""
from __future__ import annotations

import logging
from typing import Sequence

from langchain_core.tools import BaseTool, tool

from .calendario import calendario
from .calendario_interno import (
    actualizar_evento, actualizar_reunion, borrar_evento, borrar_reunion,
    buscar_evento, buscar_reunion, crear_evento, crear_reunion,
)
from .djs import actualizar_dj, consultar_dj, registrar_dj
from .memoria import memoria
from .salones import salones

log = logging.getLogger("agents.tools")


@tool("pensar")
def pensar(pensamiento: str) -> dict:
    """Anotá tu razonamiento antes de decidir. No consulta ni cambia nada.

    Args:
        pensamiento: lo que estás evaluando.
    """
    return {"ok": True}


# Alcance por audiencia. Las de escritura existen SOLO para "interno"; el toolbelt del
# cliente final no las tiene bindeadas y por eso no hay prompt que las pueda alcanzar.
_POR_AUDIENCIA: dict[str, list[BaseTool]] = {
    "externo": [memoria, calendario, salones, pensar],
    "interno": [
        memoria, pensar,
        buscar_evento, crear_evento, actualizar_evento, borrar_evento,
        buscar_reunion, crear_reunion, actualizar_reunion, borrar_reunion,
        consultar_dj, registrar_dj, actualizar_dj,
    ],
}

# Nombres que una tool de lectura no puede tener. Se verifica en tests: es la red que
# atrapa el día que alguien agregue una tool de escritura al toolbelt del cliente.
VERBOS_DE_ESCRITURA = ("crear", "actualizar", "borrar", "eliminar", "escribir",
                       "asignar", "ingestar", "modificar", "reservar")


def para(audiencia: str) -> Sequence[BaseTool]:
    if audiencia not in _POR_AUDIENCIA:
        raise ValueError(
            f"no hay toolbelt definido para la audiencia '{audiencia}' "
            f"(disponibles: {sorted(_POR_AUDIENCIA)})"
        )
    return _POR_AUDIENCIA[audiencia]


def por_nombre(audiencia: str) -> dict[str, BaseTool]:
    return {t.name: t for t in para(audiencia)}
