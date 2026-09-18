"""Tool de memoria: búsqueda en el vector store de SONNER (solo lectura).

Acá estaba el LLM anidado más caro: el agente principal mandaba un comando en texto, un
segundo LLM elegía la fuente, llamaba a pgvector y **volvía a redactar** los chunks que
ya tenía que devolver verbatim. Dos llamadas a modelo para una búsqueda.

Ahora el agente principal elige la fuente como argumento y `memoria.consultar` hace la
búsqueda y arma la respuesta de forma determinista, con el mismo contrato de antes
—incluido el prefijo literal "[INTERNO — NO COMUNICAR AL CLIENTE]" que el prompt del
agente principal busca para saber qué ocultar.
"""
from __future__ import annotations

from typing import Literal, Optional

from langchain_core.tools import tool

from ...services.memoria import memoria as det

Fuente = Literal["materiales", "eventos", "modelo_eventos", "informacion_interna", "todas"]


@tool("memoria")
def memoria(consulta: str, fuente: Optional[Fuente] = None) -> dict:
    """Busca en la base de conocimiento interna de SONNER.

    Args:
        consulta: qué buscar, en palabras (por ejemplo "parlantes disponibles").
        fuente: dónde buscar.
            - "materiales": stock, equipos, cantidades.
            - "eventos": histórico de eventos, fechas, salones.
            - "modelo_eventos": configuraciones técnicas CFG-XXX y precio sugerido.
            - "informacion_interna": políticas, señas, condiciones de reserva.
            - "todas": si no sabés cuál corresponde.

    Devuelve {origen, encontrado, respuesta}. Todo lo que venga prefijado con
    "[INTERNO — NO COMUNICAR AL CLIENTE]" es para vos, no para el cliente.
    """
    consulta = (consulta or "").strip()
    if not consulta:
        return {"error": "consulta vacía"}
    salida = det.consultar(consulta, fuente=fuente)
    # El _meta es ruido para el contexto del modelo.
    return {"origen": salida.get("origen"), "encontrado": salida.get("encontrado"),
            "respuesta": salida.get("respuesta")}
