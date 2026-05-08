"""
Service de credenciales editables.
Las credenciales viven en la tabla `app_settings` de Supabase y se acceden
con la SERVICE_ROLE_KEY (saltea RLS). Hay cache en memoria para no martillar
la DB en cada request.

Si la SERVICE_ROLE_KEY no está configurada o la credencial no existe en DB,
hace fallback a la env var con el mismo nombre.
"""
import os
import time
import logging
import threading
from typing import Any
from supabase import create_client, Client

from ..config import settings

logger = logging.getLogger(__name__)

_cache: dict[str, tuple[str | None, float]] = {}
_cache_lock = threading.Lock()
TTL = 30  # segundos

_admin_client: Client | None = None


def _admin() -> Client | None:
    """Cliente Supabase con service_role (saltea RLS). Devuelve None si no hay key."""
    global _admin_client
    if _admin_client is not None:
        return _admin_client
    key = settings.SUPABASE_SERVICE_ROLE_KEY or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not key:
        logger.warning("SUPABASE_SERVICE_ROLE_KEY no configurada — usando solo env vars como fallback")
        return None
    _admin_client = create_client(settings.SUPABASE_URL, key)
    return _admin_client


def get(key: str, default: str | None = None) -> str | None:
    """
    Lee credencial: cache → Supabase → env var → default.
    """
    now = time.time()
    with _cache_lock:
        if key in _cache and _cache[key][1] > now:
            return _cache[key][0]

    val: str | None = None
    sb = _admin()
    if sb is not None:
        try:
            res = sb.table("app_settings").select("value").eq("key", key).maybe_single().execute()
            if res and res.data and res.data.get("value"):
                val = res.data["value"]
        except Exception as e:
            logger.warning("Error leyendo credencial %s desde Supabase: %s", key, e)

    if not val:
        val = os.getenv(key) or default

    with _cache_lock:
        _cache[key] = (val, now + TTL)
    return val


def set(key: str, value: str) -> bool:
    """Guarda/actualiza credencial. Devuelve True si se guardó."""
    sb = _admin()
    if sb is None:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY no configurada — no puedo escribir credenciales")
    sb.table("app_settings").update(
        {"value": value, "updated_at": "now()"}
    ).eq("key", key).execute()
    invalidate(key)
    return True


def invalidate(key: str | None = None) -> None:
    """Limpia el cache de una key (o todo si key=None)."""
    with _cache_lock:
        if key is None:
            _cache.clear()
        else:
            _cache.pop(key, None)


def list_all() -> list[dict[str, Any]]:
    """
    Lista todas las credenciales con metadata.
    NUNCA devuelve los valores reales de las que `is_secret=true`,
    solo si están seteadas o no.
    """
    sb = _admin()
    if sb is None:
        return []
    res = sb.table("app_settings").select(
        "key, category, description, is_secret, value, updated_at"
    ).order("category").order("key").execute()

    out = []
    for r in (res.data or []):
        v = r.get("value")
        is_set = bool(v) or bool(os.getenv(r["key"]))
        item = {
            "key":         r["key"],
            "category":    r.get("category", "general"),
            "description": r.get("description", ""),
            "is_secret":   r.get("is_secret", True),
            "is_set":      is_set,
            "updated_at":  r.get("updated_at"),
        }
        # Solo devolvemos value si NO es secret
        if not r.get("is_secret"):
            item["value"] = v or os.getenv(r["key"]) or ""
        out.append(item)
    return out
