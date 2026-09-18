"""Tool de calendario: disponibilidad de una fecha (solo lectura).

Antes el agente principal tenía que armar el string exacto
`verificar disponibilidad evento [FECHA]` para que un subagente LLM lo interpretara y
llamara a Google. Ahora el modelo pasa una fecha y Python hace el resto: una llamada a
LLM menos, y un modo menos de fallar (el string mal armado devolvía "no pude interpretar
la fecha" sin que nadie se enterara).
"""
from __future__ import annotations

from langchain_core.tools import tool

from ...services.agente_externo import tools_google


@tool("calendario")
def calendario(fecha: str) -> dict:
    """Consulta si una fecha está libre en el calendario de eventos de SONNER.

    Args:
        fecha: la fecha a consultar en formato YYYY-MM-DD (por ejemplo "2026-12-13").

    Devuelve `estado`: "disponible" (ningún evento), "ocupado_parcial" (uno) u "ocupado"
    (dos o más), junto con `cantidad_eventos` y `tipo_evento`. Si da "error" no pudo
    consultarse: no le afirmes al cliente que la fecha está libre, derivá a Gabriel.
    Nunca expone montos ni señas.
    """
    return tools_google.disponibilidad(fecha)
