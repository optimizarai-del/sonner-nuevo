"""
Auth service: password hashing (bcrypt), JWT create/decode, lookup de usuarios.
La tabla `users` está protegida con RLS — se accede solo con service_role.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..config import settings
from . import credentials as creds_service

logger = logging.getLogger(__name__)

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_bearer = HTTPBearer(auto_error=False)


# ── Cliente Supabase service_role ────────────────────────────────────────────
def _sb_admin():
    """Reusa el cliente service_role del módulo credentials."""
    sb = creds_service._admin()
    if sb is None:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY no configurada — auth deshabilitado")
    return sb


# ── Password hashing ─────────────────────────────────────────────────────────
def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _pwd_context.verify(plain, hashed)
    except Exception:
        return False


# ── JWT ──────────────────────────────────────────────────────────────────────
def create_token(user: dict) -> str:
    """Crea un JWT con datos del usuario."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub":      str(user["id"]),
        "username": user["username"],
        "name":     user.get("name", ""),
        "role":     user.get("role", "armador"),
        "iat":      int(now.timestamp()),
        "exp":      int((now + timedelta(hours=settings.JWT_EXPIRATION_HOURS)).timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decodifica + valida el JWT. Lanza HTTPException si es inválido."""
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Token inválido: {e}")


# ── Dependencies para FastAPI ────────────────────────────────────────────────
def get_current_user(
    cred: HTTPAuthorizationCredentials = Depends(_bearer),
) -> dict:
    """Extrae y valida el JWT del header `Authorization: Bearer <token>`."""
    if cred is None:
        raise HTTPException(status_code=401, detail="Falta header Authorization")
    return decode_token(cred.credentials)


def require_role(*allowed_roles: str):
    """Dependency factory: protege un endpoint a uno o varios roles."""
    def _check(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Acceso denegado. Roles permitidos: {', '.join(allowed_roles)}",
            )
        return user
    return _check


# ── DB helpers ───────────────────────────────────────────────────────────────
def find_user_by_username(username: str) -> dict | None:
    sb = _sb_admin()
    res = sb.table("users").select("*").eq("username", username.strip().lower()).eq("active", True).maybe_single().execute()
    return res.data if res and res.data else None


def find_user_by_id(user_id: str) -> dict | None:
    sb = _sb_admin()
    res = sb.table("users").select("*").eq("id", user_id).maybe_single().execute()
    return res.data if res and res.data else None


def update_last_login(user_id: str) -> None:
    try:
        _sb_admin().table("users").update(
            {"last_login": datetime.now(timezone.utc).isoformat()}
        ).eq("id", user_id).execute()
    except Exception as e:
        logger.warning("No se pudo actualizar last_login: %s", e)


def list_users() -> list[dict]:
    sb = _sb_admin()
    res = sb.table("users").select(
        "id, username, name, role, active, last_login, created_at"
    ).order("created_at").execute()
    return res.data or []


def create_user(username: str, password: str, name: str, role: str) -> dict:
    if role not in ("admin", "armador", "mayorista", "deposito"):
        raise ValueError(f"Rol inválido: {role}")
    sb = _sb_admin()
    payload = {
        "username":      username.strip().lower(),
        "password_hash": hash_password(password),
        "name":          name.strip(),
        "role":          role,
        "active":        True,
    }
    res = sb.table("users").insert(payload).execute()
    return res.data[0] if res.data else None


def update_user(user_id: str, fields: dict[str, Any]) -> dict | None:
    """Actualiza usuario. Si `password` viene, se hashea."""
    sb = _sb_admin()
    safe = {}
    if "name" in fields:     safe["name"] = fields["name"].strip()
    if "role" in fields:
        if fields["role"] not in ("admin", "armador", "mayorista", "deposito"):
            raise ValueError("Rol inválido")
        safe["role"] = fields["role"]
    if "active" in fields:   safe["active"] = bool(fields["active"])
    if "password" in fields and fields["password"]:
        safe["password_hash"] = hash_password(fields["password"])
    safe["updated_at"] = datetime.now(timezone.utc).isoformat()
    res = sb.table("users").update(safe).eq("id", user_id).execute()
    return res.data[0] if res.data else None


def deactivate_user(user_id: str) -> None:
    """Soft delete: solo desactiva."""
    _sb_admin().table("users").update({"active": False}).eq("id", user_id).execute()
