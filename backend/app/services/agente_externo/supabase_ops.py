"""Operaciones sobre Supabase que hacía n8n en el pipeline del agente externo:

- `automatizacion_activa()`  → kill-switch global (automatizacion_config.activa, id=1).
- `esta_bloqueado(tel)`      → blocklist por últimos 10 dígitos.
- `tipo_cliente(tel)`        → 'mayorista' | 'minorista' (RPC es_mayorista, fallback minorista).
- `contexto_reunion(tel)`    → próxima reunión 'agendada' futura del cliente.

Todo best-effort: si algo falla, devolvemos el valor seguro (automatización ON, no
bloqueado, minorista, sin reunión) para no cortar la atención por un error de infra.
"""
from __future__ import annotations

import logging
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from .. import credentials as creds_service

log = logging.getLogger("agente_externo.supabase_ops")

_TZ_AR = timezone(timedelta(hours=-3))


def _sb():
    sb = creds_service._admin()
    if sb is None:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY no configurada")
    return sb


def _ultimos10(tel: str) -> str:
    return re.sub(r"[^0-9]", "", str(tel or ""))[-10:]


# ── Kill-switch global ────────────────────────────────────────────────────────
def automatizacion_activa() -> bool:
    """SELECT activa FROM automatizacion_config WHERE id=1. Ante error → True (no cortar)."""
    try:
        res = _sb().table("automatizacion_config").select("activa").eq("id", 1).maybe_single().execute()
        if res and res.data is not None:
            return bool(res.data.get("activa", True))
    except Exception as e:  # noqa: BLE001
        log.warning("automatizacion_config no disponible (%s) — asumo activa", e)
    return True


# ── Blocklist (cache con TTL) ─────────────────────────────────────────────────
_bl_cache: dict[str, Any] = {"data": None, "exp": 0.0}
_bl_lock = threading.Lock()
_BL_TTL = 60.0


def _cargar_blocklist() -> set[str]:
    now = time.time()
    with _bl_lock:
        if _bl_cache["data"] is not None and _bl_cache["exp"] > now:
            return _bl_cache["data"]
    nums: set[str] = set()
    try:
        res = _sb().table("blocklist").select("identifier").execute()
        for row in (res.data or []):
            u10 = _ultimos10(row.get("identifier") or "")
            if len(u10) >= 8:
                nums.add(u10)
    except Exception as e:  # noqa: BLE001
        log.warning("No se pudo cargar blocklist: %s", e)
    with _bl_lock:
        _bl_cache["data"] = nums
        _bl_cache["exp"] = now + _BL_TTL
    return nums


def esta_bloqueado(tel: str) -> bool:
    u10 = _ultimos10(tel)
    if len(u10) < 8:
        return False
    return u10 in _cargar_blocklist()


# ── Mayorista / minorista ─────────────────────────────────────────────────────
_RPC_PARAMS = ("telefono", "p_telefono", "identifier", "tel", "numero")


def tipo_cliente(tel: str) -> str:
    """'mayorista' si la RPC es_mayorista da true; si no o ante error → 'minorista'."""
    sb = None
    try:
        sb = _sb()
    except Exception:
        return "minorista"
    for pname in _RPC_PARAMS:
        try:
            res = sb.rpc("es_mayorista", {pname: tel}).execute()
            val = res.data
            if isinstance(val, list):
                val = val[0] if val else None
            if isinstance(val, dict):
                val = next(iter(val.values()), None)
            if val is True:
                return "mayorista"
            if val is False:
                return "minorista"
        except Exception:
            continue
    return "minorista"


# ── Contexto de reunión ───────────────────────────────────────────────────────
_DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
_MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
          "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def _fmt_fecha(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00")).astimezone(_TZ_AR)
        return f"{_DIAS[dt.weekday()]} {dt.day} de {_MESES[dt.month - 1]} a las {dt:%H:%M}"
    except Exception:
        return str(iso)


def contexto_reunion(tel: str) -> dict[str, Any]:
    """Próxima reunión 'agendada' futura del cliente. {tiene, fecha_hora_texto, titulo}."""
    vacio = {"tiene": False, "fecha_hora_texto": None, "titulo": None}
    u10 = _ultimos10(tel)
    if len(u10) < 8:
        return vacio
    try:
        ahora = datetime.now(timezone.utc).isoformat()
        res = (
            _sb().table("reuniones")
            .select("nombre, telefono, fecha_hora, evento, estado")
            .eq("estado", "agendada")
            .gte("fecha_hora", ahora)
            .order("fecha_hora", desc=False)
            .limit(50)
            .execute()
        )
        for row in (res.data or []):
            if _ultimos10(row.get("telefono") or "") == u10:
                return {
                    "tiene": True,
                    "fecha_hora_texto": _fmt_fecha(row.get("fecha_hora")),
                    "titulo": row.get("evento") or None,
                }
    except Exception as e:  # noqa: BLE001
        log.warning("contexto_reunion falló: %s", e)
    return vacio
