"""Tool de salones: auditoría técnica y comercial (solo lectura).

Los vetos (electricidad, habilitación, exclusividad) y la capacidad se resuelven en
`tools_google.evaluar_salon`, que es una función pura. El modelo no decide si un salón
es apto: solo dice cuál mirar y para cuánta gente.
"""
from __future__ import annotations

from typing import Optional

from langchain_core.tools import tool

from ...services.agente_externo import tools_google


@tool("salones")
def salones(salon: str, pax: Optional[int] = None) -> dict:
    """Verifica si un salón es apto para un evento de SONNER.

    Args:
        salon: nombre del salón tal como lo dijo el cliente (por ejemplo "Royal").
        pax: cantidad de personas, si el cliente la mencionó. Omitir si no la dio.

    Devuelve `compatibilidad`: "compatible", "incompatible" (con el `motivo`) o
    "especial" (falta un dato o hay que relevarlo a mano).

    El resultado es INTERNO. Si da "incompatible" o "especial" NO se lo expliques al
    cliente: derivá a Gabriel. Esta herramienta no cotiza precios.
    """
    return tools_google.salon(salon, pax)
