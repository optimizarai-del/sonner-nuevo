"""Historial de conversación del Analista IA, persistido por usuario en Supabase.

Tabla `analista_historial` (username, role, content, created_at), accedida con
service_role. Se carga el contexto reciente en cada consulta y se guarda cada
intercambio (pregunta del usuario + respuesta del analista).
"""
import logging
from typing import Any

from . import credentials as creds_service

logger = logging.getLogger(__name__)

TABLE = "analista_historial"
# Cuántos mensajes recientes se reinyectan como contexto (pares user/assistant).
CONTEXT_LIMIT = 12


def _sb():
    sb = creds_service._admin()
    if sb is None:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY no configurada — historial deshabilitado")
    return sb


def guardar(username: str, role: str, content: str) -> None:
    """Persiste un mensaje. Nunca rompe el flujo del analista si falla."""
    if not username or not content:
        return
    try:
        _sb().table(TABLE).insert({
            "username": username,
            "role": role,
            "content": content[:8000],
        }).execute()
    except Exception as e:  # noqa: BLE001
        logger.warning("No se pudo guardar historial del analista: %s", e)


def cargar(username: str, limit: int = CONTEXT_LIMIT) -> list[dict[str, str]]:
    """Últimos `limit` mensajes del usuario, en orden cronológico (viejo→nuevo).

    Devuelve [{role, content}] listo para anteponer a los mensajes de Anthropic.
    """
    if not username:
        return []
    try:
        res = (
            _sb().table(TABLE)
            .select("role, content, created_at")
            .eq("username", username)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        rows = res.data or []
    except Exception as e:  # noqa: BLE001
        logger.warning("No se pudo cargar historial del analista: %s", e)
        return []
    rows.reverse()  # cronológico
    return [{"role": r["role"], "content": r["content"]} for r in rows
            if r.get("role") in ("user", "assistant") and r.get("content")]


def listar(username: str, limit: int = 100) -> list[dict[str, Any]]:
    """Historial completo (para mostrarlo en la UI), cronológico."""
    if not username:
        return []
    try:
        res = (
            _sb().table(TABLE)
            .select("id, role, content, created_at")
            .eq("username", username)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        rows = res.data or []
    except Exception as e:  # noqa: BLE001
        logger.warning("No se pudo listar historial del analista: %s", e)
        return []
    rows.reverse()
    return rows


def borrar(username: str) -> int:
    """Borra todo el historial del usuario. Devuelve cuántos borró (best-effort)."""
    if not username:
        return 0
    try:
        res = _sb().table(TABLE).delete().eq("username", username).execute()
        return len(res.data or [])
    except Exception as e:  # noqa: BLE001
        logger.warning("No se pudo borrar historial del analista: %s", e)
        return 0
