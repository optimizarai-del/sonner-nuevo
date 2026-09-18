"""Tools de la planilla de DJs (solo para el agente interno)."""
from __future__ import annotations

from langchain_core.tools import tool

from ...services.agente_interno import djs as hoja


@tool("consultar_dj")
def consultar_dj(dj: str, fecha: str) -> dict:
    """Verifica si un DJ está libre en una fecha.

    Args:
        dj: nombre del DJ.
        fecha: la fecha a consultar, YYYY-MM-DD.

    `disponible: true` significa que no tiene ningún evento cargado ese día.
    Si viene `disponible: null` no se pudo determinar: no afirmes que está libre.
    """
    return hoja.disponibilidad(dj, fecha)


@tool("registrar_dj")
def registrar_dj(dj: str, fecha: str, tipo_evento: str = "", salon: str = "",
                 valor: str = "", pagado: str = "", asignado_por: str = "",
                 observaciones: str = "") -> dict:
    """Asigna un DJ a un evento, agregando una fila a la planilla.

    Consultá antes con `consultar_dj` que esté libre.

    Args:
        dj: nombre del DJ.
        fecha: fecha del evento, YYYY-MM-DD.
        tipo_evento: casamiento, cumpleaños, corporativo, etc.
        salon: dónde es.
        valor: cachet acordado.
        pagado: "si" o "no".
        asignado_por: quién lo asignó.
        observaciones: lo que haga falta aclarar.
    """
    return hoja.registrar(dj, fecha, tipo_evento, salon, valor, pagado,
                          asignado_por, observaciones)


@tool("actualizar_dj")
def actualizar_dj(dj: str, fecha: str, cambios: dict) -> dict:
    """Modifica una asignación de DJ ya cargada.

    Args:
        dj: nombre del DJ.
        fecha: fecha del evento, YYYY-MM-DD.
        cambios: qué columnas cambiar, por nombre. Válidas: FECHA, TIPO DE EVENTO,
            SALON, DJ, VALOR, PAGADO, ASIGNADO POR, OBSERVACIONES.
            Ejemplo: {"PAGADO": "si", "VALOR": "180000"}.

    Si hay más de un registro para ese DJ y fecha no se modifica nada y se devuelven
    los candidatos: preguntale al usuario cuál.
    """
    return hoja.actualizar(dj, fecha, cambios or {})
