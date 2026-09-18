"""Tools de calendario del agente interno.

Ninguna tool de escritura recibe el calendario como argumento: cada una tiene su destino
fijo en el código. Es la diferencia con n8n, donde el calendario era un parámetro que el
LLM elegía guiado por el prompt — y por lo tanto podía elegir mal. Acá no existe una
forma de que `crear_evento` escriba en "fiestas cromo".
"""
from __future__ import annotations

from typing import Optional

from langchain_core.tools import tool

from ...services.agente_interno import calendario as cal

_EVENTOS = "eventos_sonner"
_REUNIONES = "reuniones_gabi"


# ── Eventos de SONNER ────────────────────────────────────────────────────────
@tool("buscar_evento")
def buscar_evento(texto: str = "", desde: Optional[str] = None,
                  hasta: Optional[str] = None) -> dict:
    """Busca eventos en los calendarios de SONNER, Tijereta y Cromo a la vez.

    Args:
        texto: qué buscar (nombre del evento, salón, cliente). Vacío trae todos.
        desde: fecha inicial YYYY-MM-DD. Por defecto, hoy.
        hasta: fecha final YYYY-MM-DD. Por defecto, un año adelante.

    Devuelve cada evento con su `event_id`, que es lo que necesitás para actualizarlo
    o borrarlo. Es el paso obligatorio antes de cualquier modificación.
    """
    return cal.buscar(texto, desde, hasta, calendarios=cal.DE_EVENTOS)


@tool("crear_evento")
def crear_evento(titulo: str, inicio: str, fin: Optional[str] = None,
                 descripcion: str = "", ubicacion: str = "") -> dict:
    """Crea un evento en el calendario de eventos de SONNER.

    Args:
        titulo: nombre del evento.
        inicio: fecha y hora de inicio, ISO (por ejemplo "2026-12-13T21:00").
        fin: fecha y hora de fin. Si se omite, se asumen 4 horas.
        descripcion: detalle del evento.
        ubicacion: salón o dirección.

    Devuelve el `event_id` generado.
    """
    return cal.crear(_EVENTOS, titulo, inicio, fin, descripcion, ubicacion)


@tool("actualizar_evento")
def actualizar_evento(event_id: str, titulo: Optional[str] = None,
                      descripcion: Optional[str] = None, inicio: Optional[str] = None,
                      fin: Optional[str] = None, ubicacion: Optional[str] = None) -> dict:
    """Modifica un evento de SONNER. Solo cambia los campos que pases.

    Args:
        event_id: el id que devolvió `buscar_evento`. Obligatorio.
        titulo: nuevo nombre, si cambia.
        descripcion: nueva descripción, si cambia.
        inicio: nueva fecha y hora de inicio, ISO, si cambia.
        fin: nueva fecha y hora de fin, ISO, si cambia.
        ubicacion: nuevo salón o dirección, si cambia.
    """
    return cal.actualizar(_EVENTOS, event_id, titulo, descripcion, inicio, fin, ubicacion)


@tool("borrar_evento")
def borrar_evento(event_id: str) -> dict:
    """Elimina un evento del calendario de SONNER.

    Args:
        event_id: el id que devolvió `buscar_evento`. Verificá con el usuario antes
            de borrar: la operación no se puede deshacer.
    """
    return cal.borrar(_EVENTOS, event_id)


# ── Agenda personal de Gabi ──────────────────────────────────────────────────
@tool("buscar_reunion")
def buscar_reunion(texto: str = "", desde: Optional[str] = None,
                   hasta: Optional[str] = None) -> dict:
    """Busca en la agenda personal de Gabi (reuniones, bloqueos, ausencias).

    Args:
        texto: qué buscar. Vacío trae todas.
        desde: fecha inicial YYYY-MM-DD. Por defecto, hoy.
        hasta: fecha final YYYY-MM-DD.
    """
    return cal.buscar(texto, desde, hasta, calendarios=("reuniones_gabi",))


@tool("crear_reunion")
def crear_reunion(titulo: str, inicio: str, fin: Optional[str] = None,
                  descripcion: str = "") -> dict:
    """Agenda una reunión o bloqueo en el calendario personal de Gabi.

    Args:
        titulo: motivo de la reunión.
        inicio: fecha y hora ISO (por ejemplo "2026-12-13T15:30").
        fin: fecha y hora de fin. Si se omite, se asumen 4 horas.
        descripcion: detalle.
    """
    return cal.crear(_REUNIONES, titulo, inicio, fin, descripcion)


@tool("actualizar_reunion")
def actualizar_reunion(event_id: str, titulo: Optional[str] = None,
                       descripcion: Optional[str] = None, inicio: Optional[str] = None,
                       fin: Optional[str] = None) -> dict:
    """Modifica una reunión de Gabi. Solo cambia los campos que pases.

    Args:
        event_id: el id que devolvió `buscar_reunion`. Obligatorio.
        titulo: nuevo motivo, si cambia.
        descripcion: nuevo detalle, si cambia.
        inicio: nueva fecha y hora ISO, si cambia.
        fin: nueva fecha y hora de fin, si cambia.
    """
    return cal.actualizar(_REUNIONES, event_id, titulo, descripcion, inicio, fin)


@tool("borrar_reunion")
def borrar_reunion(event_id: str) -> dict:
    """Cancela una reunión de la agenda de Gabi.

    Args:
        event_id: el id que devolvió `buscar_reunion`.
    """
    return cal.borrar(_REUNIONES, event_id)
