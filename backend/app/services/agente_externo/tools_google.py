"""Acceso a Google Calendar y Sheets, y las reglas de negocio que se aplican encima.

Reemplazan a los subagentes n8n `agente_calendario` y `AGENTE DE SALONES`. Las reglas
que esos prompts le pedían al LLM (umbrales de ocupación, vetos técnicos y comerciales,
no exponer montos) viven acá como funciones puras: no son alucinables y se testean sin red.

El módulo está partido en tres capas:
1. `_credentials` / `_leer_*`  → I/O contra Google.
2. `estado_por_eventos`, `evaluar_salon`, `_datos_fila` → decisión pura, sin I/O.
3. `disponibilidad(fecha)` / `salon(nombre, pax)` → la API tipada que usan las tools.

`verificar_disponibilidad(consulta)` y `verificar_salon(consulta)` quedan como envoltorios
que parsean el string estilo n8n; los usa el camino de rollback y `/api/agente/diag`.

Si Google falla o las credenciales no tienen scope, se degrada al valor seguro
(estado 'error' / compatibilidad 'especial') y el agente deriva a Gabriel.
"""
from __future__ import annotations

import logging
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from ...config import settings
from .. import credentials as creds
from .. import google_auth

log = logging.getLogger("agente_externo.tools_google")

_TZ_AR = timezone(timedelta(hours=-3))

# Umbrales de ocupación del día. Venían del prompt del subagente de calendario.
OCUPADO_PARCIAL_DESDE = 1
OCUPADO_DESDE = 2

# Lo que nunca sale del título de un evento hacia el agente: montos y señas.
_RE_MONTOS = re.compile(r"\$\s?[\d\.]+|seña[^,]*", re.I)


def _credentials() -> Credentials:
    """Credenciales de solo lectura: el agente externo nunca escribe."""
    return google_auth.credenciales(google_auth.SCOPES_LECTURA)


def diagnostico_google() -> dict[str, Any]:
    """Prueba mínima de Calendar + Sheets con el error CRUDO de Google si falla."""
    res: dict[str, Any] = {}
    try:
        cal = build("calendar", "v3", credentials=_credentials(), cache_discovery=False)
        cal.events().list(calendarId=settings.GCAL_EVENTOS_ID, maxResults=1,
                          timeZone="America/Argentina/Buenos_Aires").execute()
        res["calendar"] = {"ok": True}
    except Exception as e:  # noqa: BLE001
        res["calendar"] = {"ok": False, "error": f"{type(e).__name__}: {e}"[:600]}
    try:
        sh = build("sheets", "v4", credentials=_credentials(), cache_discovery=False)
        sh.spreadsheets().values().get(
            spreadsheetId=settings.GSHEET_SALONES_ID, range="A1:B2").execute()
        res["sheets"] = {"ok": True}
    except Exception as e:  # noqa: BLE001
        res["sheets"] = {"ok": False, "error": f"{type(e).__name__}: {e}"[:600]}
    cid = creds.get("GOOGLE_CLIENT_ID", settings.GOOGLE_CLIENT_ID) or ""
    rt = creds.get("GOOGLE_REFRESH_TOKEN", settings.GOOGLE_REFRESH_TOKEN) or ""
    res["creds"] = {"client_id_tail": cid[-24:], "has_refresh_token": bool(rt),
                    "calendar_id": settings.GCAL_EVENTOS_ID, "sheet_id": settings.GSHEET_SALONES_ID}
    return res


# ── Calendario ───────────────────────────────────────────────────────────────
def normalizar_fecha(texto: str) -> Optional[str]:
    """'YYYY-MM-DD' desde texto libre. Acepta YYYY-MM-DD y DD/MM/YYYY."""
    if not texto:
        return None
    m = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", texto)
    if m:
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    m = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", texto)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if y < 100:
            y += 2000
        return f"{y:04d}-{mo:02d}-{d:02d}"
    return None


def estado_por_eventos(cantidad: int) -> str:
    """0 → disponible · 1 → ocupado_parcial · 2 o más → ocupado."""
    if cantidad >= OCUPADO_DESDE:
        return "ocupado"
    if cantidad >= OCUPADO_PARCIAL_DESDE:
        return "ocupado_parcial"
    return "disponible"


def titulos_sin_montos(eventos: list[dict[str, Any]]) -> list[str]:
    """Títulos de los eventos con montos y señas removidos (regla de privacidad)."""
    limpios = [_RE_MONTOS.sub("", (e.get("summary") or "")).strip() for e in eventos]
    return [t for t in limpios if t]


def _leer_eventos(fecha: str) -> list[dict[str, Any]]:
    cal = build("calendar", "v3", credentials=_credentials(), cache_discovery=False)
    dia = datetime.strptime(fecha, "%Y-%m-%d").replace(tzinfo=_TZ_AR)
    res = cal.events().list(
        calendarId=settings.GCAL_EVENTOS_ID,
        timeMin=dia.replace(hour=0, minute=0, second=0).isoformat(),
        timeMax=dia.replace(hour=23, minute=59, second=59).isoformat(),
        singleEvents=True, orderBy="startTime", timeZone="America/Argentina/Buenos_Aires",
    ).execute()
    return [e for e in (res.get("items") or []) if e.get("status") != "cancelled"]


def disponibilidad(fecha: str) -> dict[str, Any]:
    """Estado del día en el calendario de eventos. `fecha` en YYYY-MM-DD."""
    fecha_norm = normalizar_fecha(fecha)
    if not fecha_norm:
        return {"fecha_evento": None, "tipo_evento": None, "cantidad_eventos": None,
                "estado": "error", "motivo": "no pude interpretar la fecha"}
    try:
        eventos = _leer_eventos(fecha_norm)
    except Exception as e:  # noqa: BLE001
        log.warning("disponibilidad(%s) falló: %s", fecha_norm, e)
        return {"fecha_evento": fecha_norm, "tipo_evento": None, "cantidad_eventos": None,
                "estado": "error", "motivo": "no pude consultar el calendario"}
    titulos = titulos_sin_montos(eventos)
    return {"fecha_evento": fecha_norm, "tipo_evento": ", ".join(titulos) or None,
            "cantidad_eventos": len(eventos), "estado": estado_por_eventos(len(eventos))}


# ── Salones ──────────────────────────────────────────────────────────────────
def _norm(s: str) -> str:
    """Minúsculas, sin acentos y sin símbolos, para comparar nombres de salón.

    Los acentos se transliteran ANTES de filtrar: si solo se borraran los caracteres no
    ASCII, "Los Álamos" quedaría como "loslamos" y no matchearía con "Los Alamos" tal
    como lo escribe el cliente, que es la mitad de los casos.
    """
    sin_tildes = unicodedata.normalize("NFKD", s or "")
    sin_tildes = "".join(c for c in sin_tildes if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", sin_tildes.lower())


def _col(headers: list[str], *claves: str) -> Optional[int]:
    for i, h in enumerate(headers):
        hn = _norm(h)
        if any(_norm(k) in hn for k in claves):
            return i
    return None


def _datos_fila(headers: list[str], fila: list[str]) -> dict[str, Any]:
    """Normaliza una fila de la planilla a los campos que miran las reglas."""
    def g(*claves: str) -> str:
        idx = _col(headers, *claves)
        return fila[idx].strip() if idx is not None and idx < len(fila) else ""

    tipo_raw = g("tipo").upper()
    return {
        "nombre": g("nombre", "salon", "id") or (fila[0].strip() if fila else ""),
        "tipo": "propio" if "PROPIO" in tipo_raw else ("externo" if "EXTERNO" in tipo_raw else "desconocido"),
        "capacidad": g("capacidad", "cap"),
        "electricidad": g("electricidad", "electrica").upper(),
        "habilitado": g("habilitado", "habilitacion").upper(),
        "exclusividad": g("exclusividad", "proveedor"),
        "observaciones": g("observaciones", "observ") or None,
    }


def evaluar_salon(datos: dict[str, Any], pax: Optional[int]) -> dict[str, Any]:
    """Aplica los vetos y la capacidad. Pura: no toca la red.

    Orden de evaluación, igual que el prompt del subagente de n8n:
    1. Veto técnico   — sin electricidad o sin habilitación → incompatible.
    2. Veto comercial — exclusividad con otro proveedor → incompatible.
    3. Capacidad      — PAX por encima del máximo → incompatible.
    4. Sin datos      — falta capacidad o falta PAX → especial (relevamiento manual).
    """
    base = {"salon": datos.get("nombre") or "", "tipo": datos.get("tipo", "desconocido"),
            "observaciones": datos.get("observaciones")}

    if datos.get("electricidad") in ("NO", "FALSE") or datos.get("habilitado") in ("NO", "FALSE"):
        return {**base, "compatibilidad": "incompatible", "capacidad_ok": None,
                "motivo": "veto técnico (electricidad/habilitación)"}

    exclusividad = datos.get("exclusividad") or ""
    if exclusividad and _norm(exclusividad) not in ("", "no", "ninguno", "ninguna"):
        return {**base, "compatibilidad": "incompatible", "capacidad_ok": None,
                "motivo": "exclusividad con otro proveedor"}

    capacidades = [int(x) for x in re.findall(r"\d+", datos.get("capacidad") or "")]
    if not capacidades or pax is None:
        return {**base, "compatibilidad": "especial", "capacidad_ok": None,
                "motivo": "capacidad sin dato o consulta sin PAX — requiere relevamiento"}
    if pax > max(capacidades):
        return {**base, "compatibilidad": "incompatible", "capacidad_ok": False,
                "motivo": "PAX excede la capacidad"}
    return {**base, "compatibilidad": "compatible", "capacidad_ok": True,
            "motivo": "apto y dentro de capacidad"}


def buscar_fila(headers: list[str], filas: list[list[str]], nombre: str) -> Optional[list[str]]:
    """Primera fila cuyo nombre matchea (comparación laxa, sin acentos ni símbolos)."""
    i_nombre = _col(headers, "nombre", "salon", "id") or 0
    objetivo = _norm(nombre)
    if not objetivo:
        return None
    for fila in filas:
        valor = _norm(fila[i_nombre] if i_nombre < len(fila) else "")
        if valor and (objetivo in valor or valor in objetivo):
            return fila
    return None


def _leer_salones() -> tuple[list[str], list[list[str]]]:
    sheets = build("sheets", "v4", credentials=_credentials(), cache_discovery=False)
    res = sheets.spreadsheets().values().get(
        spreadsheetId=settings.GSHEET_SALONES_ID, range="A1:Z1000").execute()
    filas = res.get("values") or []
    return (filas[0], filas[1:]) if filas else ([], [])


def salon(nombre: str, pax: Optional[int] = None) -> dict[str, Any]:
    """Compatibilidad técnica y comercial de un salón. Resultado INTERNO."""
    nombre = (nombre or "").strip()
    indeterminado = {"salon": nombre, "compatibilidad": "especial", "tipo": "desconocido",
                     "capacidad_ok": None, "motivo": "", "observaciones": None}
    if not nombre:
        return {**indeterminado, "motivo": "no pude interpretar el nombre del salón"}
    try:
        headers, filas = _leer_salones()
    except Exception as e:  # noqa: BLE001
        log.warning("salon(%s) falló: %s", nombre, e)
        return {**indeterminado,
                "motivo": "error al consultar la base, requiere revisión manual"}
    if not filas:
        return {**indeterminado, "motivo": "base de salones vacía"}

    fila = buscar_fila(headers, filas, nombre)
    if fila is None:
        return {**indeterminado,
                "motivo": "salón no encontrado — verificar posible error de tipeo en el nombre"}
    return evaluar_salon(_datos_fila(headers, fila), pax)


# ── Envoltorios estilo n8n (rollback y /api/agente/diag) ─────────────────────
def parsear_salon_pax(consulta: str) -> tuple[str, Optional[int]]:
    """'verificar_salon: NOMBRE para 120 personas' → ('NOMBRE', 120)."""
    txt = re.sub(r"(?i)^\s*verificar_salon\s*:", "", consulta or "").strip()
    pax = None
    m = re.search(r"(?i)para\s+(\d+)\s*personas", txt)
    if m:
        pax = int(m.group(1))
        txt = txt[: m.start()].strip()
    elif (m2 := re.search(r"(\d+)", txt)):
        pax = int(m2.group(1))
    return re.sub(r"(?i)\bpara\b.*$", "", txt).strip(" -:"), pax


def verificar_disponibilidad(consulta: str) -> dict[str, Any]:
    return disponibilidad(consulta)


def verificar_salon(consulta: str) -> dict[str, Any]:
    nombre, pax = parsear_salon_pax(consulta)
    return salon(nombre, pax)
