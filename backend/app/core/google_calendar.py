import os
from googleapiclient.discovery import build
from .google_auth import get_credentials

CALENDAR_EVENTOS_SONNER  = os.getenv("GOOGLE_CALENDAR_EVENTOS_SONNER")
CALENDAR_FIESTAS_TIJERETA = os.getenv("GOOGLE_CALENDAR_FIESTAS_TIJERETA")
CALENDAR_FIESTAS_CROMO   = os.getenv("GOOGLE_CALENDAR_FIESTAS_CROMO")
CALENDAR_REUNIONES       = os.getenv("GOOGLE_CALENDAR_REUNIONES")

TZ = "America/Argentina/Buenos_Aires"


def _service():
    return build("calendar", "v3", credentials=get_credentials(), cache_discovery=False)


# ── Lectura ────────────────────────────────────────────────────────────────────

def get_events_in_range(calendar_id: str, time_min: str, time_max: str) -> list[dict]:
    result = _service().events().list(
        calendarId=calendar_id,
        timeMin=time_min,
        timeMax=time_max,
        singleEvents=True,
        orderBy="startTime",
        timeZone=TZ,
    ).execute()
    return result.get("items", [])


def encontrar_evento_sonner(time_min: str, time_max: str) -> dict:
    """Busca eventos en los 3 calendarios de lectura simultáneamente."""
    results = {}
    for name, cal_id in [
        ("eventos_sonner",    CALENDAR_EVENTOS_SONNER),
        ("fiestas_tijereta",  CALENDAR_FIESTAS_TIJERETA),
        ("fiestas_cromo",     CALENDAR_FIESTAS_CROMO),
    ]:
        try:
            results[name] = get_events_in_range(cal_id, time_min, time_max)
        except Exception as e:
            results[name] = {"error": str(e)}
    return results


def get_availability_sonner(time_min: str, time_max: str) -> list[dict]:
    """Retorna los eventos de Eventos Sonner en el rango para chequear disponibilidad."""
    return get_events_in_range(CALENDAR_EVENTOS_SONNER, time_min, time_max)


def get_event(calendar_id: str, event_id: str) -> dict:
    return _service().events().get(
        calendarId=calendar_id,
        eventId=event_id,
        timeZone=TZ,
    ).execute()


def encontrar_reunion(event_id: str) -> dict:
    """Obtiene un evento del calendario Reuniones Gabi por ID."""
    return get_event(CALENDAR_REUNIONES, event_id)


# ── Crear ──────────────────────────────────────────────────────────────────────

def _create_event(calendar_id: str, summary: str, start: str, end: str,
                  description: str = "", location: str = "") -> dict:
    body = {
        "summary": summary,
        "description": description,
        "location": location,
        "start": {"dateTime": start, "timeZone": TZ},
        "end":   {"dateTime": end,   "timeZone": TZ},
        "colorId": "6",
        "sendUpdates": "all",
    }
    return _service().events().insert(calendarId=calendar_id, body=body).execute()


def crear_evento_sonner(summary: str, start: str, end: str,
                        description: str = "", location: str = "") -> dict:
    return _create_event(CALENDAR_EVENTOS_SONNER, summary, start, end, description, location)


def crear_reunion(summary: str, start: str, end: str,
                  description: str = "", location: str = "") -> dict:
    return _create_event(CALENDAR_REUNIONES, summary, start, end, description, location)


# ── Actualizar ─────────────────────────────────────────────────────────────────

def actualizar_evento_sonner(event_id: str, summary: str = None,
                             description: str = None) -> dict:
    """Actualiza título y/o descripción — sin cambiar fechas."""
    event = get_event(CALENDAR_EVENTOS_SONNER, event_id)
    if summary is not None:
        event["summary"] = summary
    if description is not None:
        event["description"] = description
    return _service().events().update(
        calendarId=CALENDAR_EVENTOS_SONNER, eventId=event_id, body=event
    ).execute()


def actualizar_fechas_sonner(event_id: str, start: str, end: str,
                             summary: str = None, description: str = None) -> dict:
    """Actualiza fechas/horarios (y opcionalmente título/descripción)."""
    event = get_event(CALENDAR_EVENTOS_SONNER, event_id)
    event["start"] = {"dateTime": start, "timeZone": TZ}
    event["end"]   = {"dateTime": end,   "timeZone": TZ}
    if summary is not None:
        event["summary"] = summary
    if description is not None:
        event["description"] = description
    return _service().events().update(
        calendarId=CALENDAR_EVENTOS_SONNER, eventId=event_id, body=event
    ).execute()


def actualizar_reunion(event_id: str, summary: str = None, start: str = None,
                       end: str = None, description: str = None) -> dict:
    event = get_event(CALENDAR_REUNIONES, event_id)
    if summary is not None:
        event["summary"] = summary
    if description is not None:
        event["description"] = description
    if start is not None:
        event["start"] = {"dateTime": start, "timeZone": TZ}
    if end is not None:
        event["end"]   = {"dateTime": end,   "timeZone": TZ}
    return _service().events().update(
        calendarId=CALENDAR_REUNIONES, eventId=event_id, body=event
    ).execute()


# ── Eliminar ───────────────────────────────────────────────────────────────────

def eliminar_evento_sonner(event_id: str) -> None:
    _service().events().delete(calendarId=CALENDAR_EVENTOS_SONNER, eventId=event_id).execute()


def borrar_reunion(event_id: str) -> None:
    _service().events().delete(calendarId=CALENDAR_REUNIONES, eventId=event_id).execute()
