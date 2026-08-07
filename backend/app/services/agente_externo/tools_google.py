"""Tools de Google del agente externo: calendario (disponibilidad) y salones.

Reemplazan los subagentes n8n `agente_calendario` (Create_Read2 / GCal) y
`AGENTE DE SALONES` (Google Sheets). Reusan el OAuth de contratos (mismos secretos);
si el token no tiene scope de Calendar/Sheets o la cuenta no es la correcta, degradan
al valor seguro (estado 'error' / compatibilidad 'especial') → el agente deriva a Gabriel.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from ...config import settings
from .. import credentials as creds

log = logging.getLogger("agente_externo.tools_google")

_TZ_AR = timezone(timedelta(hours=-3))
# El agente solo LEE Calendar y Sheets. Scopes mínimos (menos fricción de consent).
_SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]


def diagnostico_google() -> dict[str, Any]:
    """Prueba mínima de Calendar + Sheets y devuelve el error CRUDO de Google si falla.

    Sirve para diagnosticar credenciales por HTTP (sin depender del panel de logs).
    """
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


def _credentials() -> Credentials:
    # Token propio del agente (Calendar+Sheets); si no está, cae al de contratos
    # (que NO tiene esos scopes → seguirá fallando hasta cargar el token correcto).
    agent_rt = creds.get("GOOGLE_AGENT_REFRESH_TOKEN", settings.GOOGLE_AGENT_REFRESH_TOKEN)
    if agent_rt:
        # El token del agente está atado al cliente OAuth propio (sonner-calendarios).
        refresh_token = agent_rt
        client_id = creds.get("GOOGLE_AGENT_CLIENT_ID", settings.GOOGLE_AGENT_CLIENT_ID) \
            or creds.get("GOOGLE_CLIENT_ID", settings.GOOGLE_CLIENT_ID)
        client_secret = creds.get("GOOGLE_AGENT_CLIENT_SECRET", settings.GOOGLE_AGENT_CLIENT_SECRET) \
            or creds.get("GOOGLE_CLIENT_SECRET", settings.GOOGLE_CLIENT_SECRET)
    else:
        # Fallback al cliente/token de contratos (sin scopes Calendar/Sheets: fallará).
        refresh_token = creds.get("GOOGLE_REFRESH_TOKEN", settings.GOOGLE_REFRESH_TOKEN)
        client_id = creds.get("GOOGLE_CLIENT_ID", settings.GOOGLE_CLIENT_ID)
        client_secret = creds.get("GOOGLE_CLIENT_SECRET", settings.GOOGLE_CLIENT_SECRET)
    if not (refresh_token and client_id and client_secret):
        raise RuntimeError("Credenciales de Google incompletas")
    return Credentials(
        token=None, refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id, client_secret=client_secret, scopes=_SCOPES,
    )


# ── Calendario: disponibilidad de UNA fecha ───────────────────────────────────
def _extraer_fecha(texto: str) -> Optional[str]:
    """Devuelve 'YYYY-MM-DD' desde el comando. Soporta YYYY-MM-DD y DD/MM/YYYY."""
    if not texto:
        return None
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", texto)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", texto)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if y < 100:
            y += 2000
        return f"{y:04d}-{mo:02d}-{d:02d}"
    return None


def verificar_disponibilidad(consulta: str) -> dict[str, Any]:
    """'verificar disponibilidad evento [FECHA]' → estado del día en Eventos Sonner."""
    fecha = _extraer_fecha(consulta)
    if not fecha:
        return {"fecha_evento": None, "tipo_evento": None, "cantidad_eventos": None,
                "estado": "error", "motivo": "no pude interpretar la fecha"}
    try:
        cal = build("calendar", "v3", credentials=_credentials(), cache_discovery=False)
        dia = datetime.strptime(fecha, "%Y-%m-%d").replace(tzinfo=_TZ_AR)
        time_min = dia.replace(hour=0, minute=0, second=0).isoformat()
        time_max = dia.replace(hour=23, minute=59, second=59).isoformat()
        res = cal.events().list(
            calendarId=settings.GCAL_EVENTOS_ID, timeMin=time_min, timeMax=time_max,
            singleEvents=True, orderBy="startTime", timeZone="America/Argentina/Buenos_Aires",
        ).execute()
        items = [e for e in (res.get("items") or []) if e.get("status") != "cancelled"]
        n = len(items)
        # tipo_evento: títulos, sin montos/señas (regla de privacidad).
        tipos = [re.sub(r"\$\s?[\d\.]+|seña[^,]*", "", (e.get("summary") or "")).strip()
                 for e in items]
        tipos = [t for t in tipos if t]
        estado = "disponible" if n == 0 else ("ocupado_parcial" if n == 1 else "ocupado")
        return {"fecha_evento": fecha, "tipo_evento": ", ".join(tipos) or None,
                "cantidad_eventos": n, "estado": estado}
    except Exception as e:  # noqa: BLE001
        log.warning("verificar_disponibilidad falló: %s", e)
        return {"fecha_evento": fecha, "tipo_evento": None, "cantidad_eventos": None,
                "estado": "error", "motivo": "no pude consultar el calendario"}


# ── Salones: apto/no apto + capacidad ─────────────────────────────────────────
def _parse_salon_pax(consulta: str) -> tuple[str, Optional[int]]:
    """'verificar_salon: NOMBRE para 120 personas' → ('NOMBRE', 120)."""
    txt = re.sub(r"(?i)^\s*verificar_salon\s*:", "", consulta or "").strip()
    pax = None
    m = re.search(r"(?i)para\s+(\d+)\s*personas", txt)
    if m:
        pax = int(m.group(1))
        txt = txt[: m.start()].strip()
    m2 = re.search(r"(\d+)", txt)
    if pax is None and m2:
        pax = int(m2.group(1))
    nombre = re.sub(r"(?i)\bpara\b.*$", "", txt).strip(" -:")
    return nombre, pax


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def _col(headers: list[str], *claves: str) -> Optional[int]:
    for i, h in enumerate(headers):
        hn = _norm(h)
        if any(_norm(k) in hn for k in claves):
            return i
    return None


def verificar_salon(consulta: str) -> dict[str, Any]:
    """'verificar_salon: NOMBRE para PAX personas' → compatibilidad (INTERNO)."""
    nombre, pax = _parse_salon_pax(consulta)
    base = {"salon": nombre, "compatibilidad": "especial", "tipo": "desconocido",
            "capacidad_ok": None, "motivo": "", "observaciones": None}
    if not nombre:
        base["motivo"] = "no pude interpretar el nombre del salón"
        return base
    try:
        sheets = build("sheets", "v4", credentials=_credentials(), cache_discovery=False)
        res = sheets.spreadsheets().values().get(
            spreadsheetId=settings.GSHEET_SALONES_ID, range="A1:Z1000",
        ).execute()
        filas = res.get("values") or []
        if len(filas) < 2:
            base["motivo"] = "base de salones vacía"
            return base
        headers = filas[0]
        i_nombre = _col(headers, "nombre", "salon", "id") or 0
        i_tipo = _col(headers, "tipo")
        i_cap = _col(headers, "capacidad", "cap")
        i_elec = _col(headers, "electricidad", "electrica")
        i_hab = _col(headers, "habilitado", "habilitacion")
        i_excl = _col(headers, "exclusividad", "proveedor")
        i_obs = _col(headers, "observaciones", "observ")

        objetivo = _norm(nombre)
        fila = None
        for row in filas[1:]:
            val = row[i_nombre] if i_nombre < len(row) else ""
            n = _norm(val)
            if n and (objetivo in n or n in objetivo):
                fila = row
                break
        if fila is None:
            base["motivo"] = "salón no encontrado — verificar posible error de tipeo en el nombre"
            return base

        def g(idx):
            return (fila[idx].strip() if idx is not None and idx < len(fila) else "")

        tipo_raw = g(i_tipo).upper()
        tipo = "propio" if "PROPIO" in tipo_raw else ("externo" if "EXTERNO" in tipo_raw else "desconocido")
        elec = g(i_elec).upper()
        hab = g(i_hab).upper()
        excl = g(i_excl)
        obs = g(i_obs) or None

        # Vetos técnicos/comerciales
        if elec in ("NO", "FALSE") or hab in ("NO", "FALSE"):
            return {"salon": nombre, "compatibilidad": "incompatible", "tipo": tipo,
                    "capacidad_ok": None, "motivo": "veto técnico (electricidad/habilitación)",
                    "observaciones": obs}
        if excl and _norm(excl) not in ("", "no", "ninguno", "ninguna"):
            return {"salon": nombre, "compatibilidad": "incompatible", "tipo": tipo,
                    "capacidad_ok": None, "motivo": "exclusividad con otro proveedor",
                    "observaciones": obs}

        # Capacidad
        cap_ok: Optional[bool] = None
        cap_raw = g(i_cap)
        cap_nums = [int(x) for x in re.findall(r"\d+", cap_raw)]
        if pax is not None and cap_nums:
            cap_ok = pax <= max(cap_nums)
        if pax is not None and cap_nums and not cap_ok:
            return {"salon": nombre, "compatibilidad": "incompatible", "tipo": tipo,
                    "capacidad_ok": False, "motivo": "PAX excede la capacidad", "observaciones": obs}
        if not cap_nums or pax is None:
            return {"salon": nombre, "compatibilidad": "especial", "tipo": tipo,
                    "capacidad_ok": None,
                    "motivo": "capacidad sin dato o consulta sin PAX — requiere relevamiento",
                    "observaciones": obs}

        return {"salon": nombre, "compatibilidad": "compatible", "tipo": tipo,
                "capacidad_ok": True, "motivo": "apto y dentro de capacidad", "observaciones": obs}
    except Exception as e:  # noqa: BLE001
        log.warning("verificar_salon falló: %s", e)
        return {"salon": nombre, "compatibilidad": "especial", "tipo": "desconocido",
                "capacidad_ok": None, "motivo": "error al consultar la base, requiere revisión manual"}
