"""Planilla de DJs: disponibilidad, alta y edición de asignaciones.

Reemplaza al subagente n8n `AGENTE DE DJS1` (un LLM con tres nodos de Sheets colgados).
La regla que aplicaba ese subagente es una sola y es binaria: si el DJ tiene un registro
en esa fecha está ocupado, si no está libre. Eso no necesita un modelo.

Columnas de la planilla:
    FECHA | TIPO DE EVENTO | SALON | DJ | VALOR | PAGADO | ASIGNADO POR | OBSERVACIONES

Las fechas se comparan normalizadas (la planilla la cargan a mano y conviven
"13/12/2026" y "2026-12-13"), y los nombres sin acentos ni mayúsculas.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from googleapiclient.discovery import build

from ...config import settings
from .. import google_auth
from ..agente_externo.tools_google import _norm, normalizar_fecha

log = logging.getLogger("agente_interno.djs")

COLUMNAS = ["FECHA", "TIPO DE EVENTO", "SALON", "DJ", "VALOR", "PAGADO",
            "ASIGNADO POR", "OBSERVACIONES"]
_RANGO = "A1:H1000"


def _servicio(escritura: bool = False):
    scopes = google_auth.SCOPES_ESCRITURA if escritura else google_auth.SCOPES_LECTURA
    return build("sheets", "v4", credentials=google_auth.credenciales(scopes),
                 cache_discovery=False)


def _hoja_id() -> str:
    if not settings.GSHEET_DJS_ID:
        raise ValueError("GSHEET_DJS_ID no está configurado")
    return settings.GSHEET_DJS_ID


def _leer() -> tuple[list[str], list[list[str]]]:
    res = _servicio().spreadsheets().values().get(
        spreadsheetId=_hoja_id(), range=_RANGO).execute()
    filas = res.get("values") or []
    return (filas[0], filas[1:]) if filas else (COLUMNAS, [])


def a_registro(headers: list[str], fila: list[str]) -> dict[str, str]:
    """Fila cruda → dict por nombre de columna, tolerando filas cortas."""
    return {
        h.strip().upper(): (fila[i].strip() if i < len(fila) else "")
        for i, h in enumerate(headers)
    }


def coincide(registro: dict[str, str], dj: str, fecha: str) -> bool:
    """True si el registro es de ese DJ en esa fecha. Pura: se testea sin red."""
    mismo_dj = _norm(registro.get("DJ", "")) == _norm(dj)
    fecha_registro = normalizar_fecha(registro.get("FECHA", ""))
    return bool(mismo_dj and fecha_registro and fecha_registro == normalizar_fecha(fecha))


def buscar_asignaciones(headers: list[str], filas: list[list[str]],
                        dj: str, fecha: str) -> list[tuple[int, dict[str, str]]]:
    """Registros de ese DJ en esa fecha, con el número de fila real de la planilla."""
    encontrados = []
    for offset, fila in enumerate(filas):
        registro = a_registro(headers, fila)
        if coincide(registro, dj, fecha):
            encontrados.append((offset + 2, registro))  # +2: fila 1 es el encabezado
    return encontrados


# ── Operaciones ──────────────────────────────────────────────────────────────
def disponibilidad(dj: str, fecha: str) -> dict[str, Any]:
    """¿Está libre ese DJ esa fecha? Ocupado = tiene al menos un registro."""
    fecha_norm = normalizar_fecha(fecha)
    if not fecha_norm:
        return {"dj": dj, "fecha": fecha, "disponible": None,
                "motivo": "no pude interpretar la fecha"}
    headers, filas = _leer()
    asignaciones = buscar_asignaciones(headers, filas, dj, fecha_norm)
    return {
        "dj": dj,
        "fecha": fecha_norm,
        "disponible": not asignaciones,
        "asignaciones": [r for _, r in asignaciones],
    }


def registrar(
    dj: str,
    fecha: str,
    tipo_evento: str = "",
    salon: str = "",
    valor: str = "",
    pagado: str = "",
    asignado_por: str = "",
    observaciones: str = "",
) -> dict[str, Any]:
    """Agrega una asignación al final de la planilla."""
    fecha_norm = normalizar_fecha(fecha)
    if not fecha_norm:
        return {"registrado": False, "motivo": "no pude interpretar la fecha"}
    fila = [fecha_norm, tipo_evento, salon, dj, valor, pagado, asignado_por, observaciones]
    _servicio(escritura=True).spreadsheets().values().append(
        spreadsheetId=_hoja_id(), range=_RANGO,
        valueInputOption="USER_ENTERED", insertDataOption="INSERT_ROWS",
        body={"values": [fila]},
    ).execute()
    log.info("DJ registrado", extra={"dj": dj, "fecha": fecha_norm})
    return {"registrado": True, "dj": dj, "fecha": fecha_norm,
            "registro": dict(zip(COLUMNAS, fila))}


def actualizar(dj: str, fecha: str, cambios: dict[str, str]) -> dict[str, Any]:
    """Modifica una asignación existente. Solo toca las columnas que vengan en `cambios`."""
    fecha_norm = normalizar_fecha(fecha)
    if not fecha_norm:
        return {"actualizado": False, "motivo": "no pude interpretar la fecha"}

    headers, filas = _leer()
    asignaciones = buscar_asignaciones(headers, filas, dj, fecha_norm)
    if not asignaciones:
        return {"actualizado": False,
                "motivo": f"no hay registro de {dj} para el {fecha_norm}"}
    if len(asignaciones) > 1:
        # Ambiguo: elegir por nuestra cuenta cuál pisar puede borrar un dato bueno.
        return {"actualizado": False, "motivo": "hay más de un registro para ese DJ y fecha",
                "asignaciones": [r for _, r in asignaciones]}

    nro_fila, registro = asignaciones[0]
    actualizado = dict(registro)
    desconocidas = [c for c in cambios if c.strip().upper() not in COLUMNAS]
    if desconocidas:
        return {"actualizado": False, "motivo": f"columnas desconocidas: {desconocidas}"}
    for columna, valor in cambios.items():
        actualizado[columna.strip().upper()] = valor

    valores = [[actualizado.get(c, "") for c in COLUMNAS]]
    _servicio(escritura=True).spreadsheets().values().update(
        spreadsheetId=_hoja_id(), range=f"A{nro_fila}:H{nro_fila}",
        valueInputOption="USER_ENTERED", body={"values": valores},
    ).execute()
    log.info("DJ actualizado", extra={"dj": dj, "fecha": fecha_norm, "fila": nro_fila})
    return {"actualizado": True, "fila": nro_fila, "registro": actualizado}
