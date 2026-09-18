"""Calendarios del agente interno: eventos de SONNER y agenda personal de Gabi.

Reemplaza al subagente n8n `agente de calendario` y sus 12 nodos. El subagente era un
LLM cuyo trabajo real era elegir el calendario correcto — una decisión que acá es una
constante.

Los permisos son la parte importante. Hay cuatro calendarios y solo dos admiten
escritura:

    eventos_sonner   lectura + escritura   calendario principal
    reuniones_gabi   lectura + escritura   agenda personal
    fiestas_tijereta SOLO LECTURA          calendario de un tercero
    fiestas_cromo    SOLO LECTURA          calendario de un tercero

En n8n esa regla estaba escrita en el prompt. Acá está en `ESCRIBIBLES` y la verifica
`_calendario_escribible()` antes de cualquier operación de escritura: aunque alguien
pase "fiestas_cromo" a una función de escritura, la llamada no sale.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from googleapiclient.discovery import build

from ...config import settings
from .. import google_auth

log = logging.getLogger("agente_interno.calendario")

_TZ_AR = timezone(timedelta(hours=-3))
_TZ_NOMBRE = "America/Argentina/Buenos_Aires"

# Calendarios que admiten escritura. Todo lo demás es de solo lectura.
ESCRIBIBLES = frozenset({"eventos_sonner", "reuniones_gabi"})
# Los que se consultan juntos cuando alguien pregunta por eventos o disponibilidad.
DE_EVENTOS = ("eventos_sonner", "fiestas_tijereta", "fiestas_cromo")


class CalendarioNoEscribible(PermissionError):
    """Se intentó escribir en un calendario de solo lectura."""


def _ids() -> dict[str, str]:
    return {
        "eventos_sonner": settings.GCAL_EVENTOS_ID,
        "reuniones_gabi": settings.GCAL_REUNIONES_ID,
        "fiestas_tijereta": settings.GCAL_TIJERETA_ID,
        "fiestas_cromo": settings.GCAL_CROMO_ID,
    }


def _id_de(calendario: str) -> str:
    cal_id = _ids().get(calendario)
    if not cal_id:
        raise ValueError(f"calendario '{calendario}' sin ID configurado")
    return cal_id


def _calendario_escribible(calendario: str) -> str:
    if calendario not in ESCRIBIBLES:
        raise CalendarioNoEscribible(
            f"'{calendario}' es de solo lectura; escribibles: {sorted(ESCRIBIBLES)}"
        )
    return _id_de(calendario)


def _servicio(escritura: bool = False):
    scopes = google_auth.SCOPES_ESCRITURA if escritura else google_auth.SCOPES_LECTURA
    return build("calendar", "v3", credentials=google_auth.credenciales(scopes),
                 cache_discovery=False)


def _resumir(evento: dict[str, Any], calendario: str) -> dict[str, Any]:
    inicio = evento.get("start") or {}
    fin = evento.get("end") or {}
    return {
        "event_id": evento.get("id"),
        "calendario": calendario,
        "titulo": evento.get("summary") or "",
        "descripcion": (evento.get("description") or "")[:500] or None,
        "inicio": inicio.get("dateTime") or inicio.get("date"),
        "fin": fin.get("dateTime") or fin.get("date"),
        "ubicacion": evento.get("location") or None,
    }


def _rango(desde: Optional[str], hasta: Optional[str]) -> tuple[str, str]:
    """Por defecto, desde hoy y hasta un año adelante."""
    hoy = datetime.now(_TZ_AR)
    ini = datetime.fromisoformat(desde).replace(tzinfo=_TZ_AR) if desde else hoy
    fin = datetime.fromisoformat(hasta).replace(tzinfo=_TZ_AR) if hasta else ini + timedelta(days=365)
    return (ini.replace(hour=0, minute=0, second=0).isoformat(),
            fin.replace(hour=23, minute=59, second=59).isoformat())


# ── Lectura ──────────────────────────────────────────────────────────────────
def buscar(
    texto: str = "",
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    calendarios: tuple[str, ...] = DE_EVENTOS,
    limite: int = 25,
) -> dict[str, Any]:
    """Busca eventos en varios calendarios y combina los resultados.

    Los calendarios sin ID configurado se saltean y se reportan en `omitidos`: es
    mejor devolver lo que hay avisando qué falta que fallar entera la consulta.
    """
    time_min, time_max = _rango(desde, hasta)
    encontrados: list[dict[str, Any]] = []
    omitidos: list[str] = []
    errores: list[str] = []

    servicio = None
    for calendario in calendarios:
        try:
            cal_id = _id_de(calendario)
        except ValueError:
            omitidos.append(calendario)
            continue
        try:
            servicio = servicio or _servicio()
            res = servicio.events().list(
                calendarId=cal_id, timeMin=time_min, timeMax=time_max,
                q=texto or None, singleEvents=True, orderBy="startTime",
                maxResults=limite, timeZone=_TZ_NOMBRE,
            ).execute()
            encontrados.extend(
                _resumir(e, calendario) for e in (res.get("items") or [])
                if e.get("status") != "cancelled"
            )
        except Exception as e:  # noqa: BLE001
            log.warning("buscar en %s falló: %s", calendario, e)
            errores.append(f"{calendario}: {e}")

    encontrados.sort(key=lambda x: x.get("inicio") or "")
    salida: dict[str, Any] = {"cantidad": len(encontrados), "eventos": encontrados[:limite]}
    if omitidos:
        salida["omitidos"] = omitidos
    if errores:
        salida["errores"] = errores
    return salida


# ── Escritura ────────────────────────────────────────────────────────────────
def crear(
    calendario: str,
    titulo: str,
    inicio: str,
    fin: Optional[str] = None,
    descripcion: str = "",
    ubicacion: str = "",
) -> dict[str, Any]:
    """Crea un evento. Devuelve el `event_id`, que es lo que hace falta para editarlo."""
    cal_id = _calendario_escribible(calendario)
    dt_inicio = datetime.fromisoformat(inicio).replace(tzinfo=_TZ_AR)
    dt_fin = (datetime.fromisoformat(fin).replace(tzinfo=_TZ_AR) if fin
              else dt_inicio + timedelta(hours=4))
    cuerpo = {
        "summary": titulo,
        "description": descripcion or None,
        "location": ubicacion or None,
        "start": {"dateTime": dt_inicio.isoformat(), "timeZone": _TZ_NOMBRE},
        "end": {"dateTime": dt_fin.isoformat(), "timeZone": _TZ_NOMBRE},
    }
    creado = _servicio(escritura=True).events().insert(
        calendarId=cal_id, body={k: v for k, v in cuerpo.items() if v is not None}).execute()
    log.info("evento creado", extra={"calendario": calendario, "event_id": creado.get("id")})
    return _resumir(creado, calendario)


def actualizar(
    calendario: str,
    event_id: str,
    titulo: Optional[str] = None,
    descripcion: Optional[str] = None,
    inicio: Optional[str] = None,
    fin: Optional[str] = None,
    ubicacion: Optional[str] = None,
) -> dict[str, Any]:
    """Modifica solo los campos que se pasan; el resto del evento queda intacto."""
    cal_id = _calendario_escribible(calendario)
    servicio = _servicio(escritura=True)
    actual = servicio.events().get(calendarId=cal_id, eventId=event_id).execute()

    if titulo is not None:
        actual["summary"] = titulo
    if descripcion is not None:
        actual["description"] = descripcion
    if ubicacion is not None:
        actual["location"] = ubicacion
    if inicio is not None:
        actual["start"] = {
            "dateTime": datetime.fromisoformat(inicio).replace(tzinfo=_TZ_AR).isoformat(),
            "timeZone": _TZ_NOMBRE,
        }
    if fin is not None:
        actual["end"] = {
            "dateTime": datetime.fromisoformat(fin).replace(tzinfo=_TZ_AR).isoformat(),
            "timeZone": _TZ_NOMBRE,
        }

    actualizado = servicio.events().update(
        calendarId=cal_id, eventId=event_id, body=actual).execute()
    log.info("evento actualizado", extra={"calendario": calendario, "event_id": event_id})
    return _resumir(actualizado, calendario)


def borrar(calendario: str, event_id: str) -> dict[str, Any]:
    cal_id = _calendario_escribible(calendario)
    _servicio(escritura=True).events().delete(calendarId=cal_id, eventId=event_id).execute()
    log.info("evento borrado", extra={"calendario": calendario, "event_id": event_id})
    return {"borrado": True, "event_id": event_id, "calendario": calendario}
