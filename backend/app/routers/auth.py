"""Router de autenticación: login, me, gestión de usuarios."""
import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from ..services import auth

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])


# ── Schemas ───────────────────────────────────────────────────────────────────
class LoginIn(BaseModel):
    username: str
    password: str


class LoginOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserCreate(BaseModel):
    username: str
    password: str = Field(min_length=4)
    name: str
    role: str  # admin | armador | mayorista


class UserUpdate(BaseModel):
    name: str | None = None
    role: str | None = None
    active: bool | None = None
    password: str | None = None  # opcional, solo si se quiere cambiar


# ── Endpoints públicos ───────────────────────────────────────────────────────
@router.post("/login", response_model=LoginOut)
def login(payload: LoginIn) -> LoginOut:
    user = auth.find_user_by_username(payload.username)
    if not user or not auth.verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
    if not user.get("active"):
        raise HTTPException(status_code=403, detail="Usuario desactivado")

    auth.update_last_login(user["id"])
    token = auth.create_token(user)

    return LoginOut(
        access_token=token,
        user={
            "id":       user["id"],
            "username": user["username"],
            "name":     user["name"],
            "role":     user["role"],
        },
    )


@router.get("/me")
def me(user: dict = Depends(auth.get_current_user)) -> dict:
    """Devuelve los datos del usuario logueado (del JWT)."""
    return {
        "id":       user["sub"],
        "username": user["username"],
        "name":     user["name"],
        "role":     user["role"],
    }


# ── Endpoints de admin: gestión de usuarios ──────────────────────────────────
@router.get("/users")
def listar(_=Depends(auth.require_role("admin"))) -> list[dict]:
    return auth.list_users()


@router.post("/users")
def crear(payload: UserCreate, _=Depends(auth.require_role("admin"))) -> dict:
    # No permitir duplicados
    existing = auth.find_user_by_username(payload.username)
    if existing:
        raise HTTPException(status_code=409, detail="El usuario ya existe")
    try:
        user = auth.create_user(
            username=payload.username,
            password=payload.password,
            name=payload.name,
            role=payload.role,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "id":       user["id"],
        "username": user["username"],
        "name":     user["name"],
        "role":     user["role"],
        "active":   user["active"],
    }


@router.put("/users/{user_id}")
def editar(
    user_id: str,
    payload: UserUpdate,
    _=Depends(auth.require_role("admin")),
) -> dict:
    fields = payload.model_dump(exclude_none=True)
    if not fields:
        raise HTTPException(status_code=400, detail="Nada que actualizar")
    try:
        user = auth.update_user(user_id, fields)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return {"id": user["id"], "username": user["username"], "name": user["name"], "role": user["role"], "active": user["active"]}


@router.delete("/users/{user_id}")
def desactivar(user_id: str, current=Depends(auth.require_role("admin"))) -> dict:
    if current["sub"] == user_id:
        raise HTTPException(status_code=400, detail="No podés desactivar tu propio usuario")
    auth.deactivate_user(user_id)
    return {"status": "ok", "deactivated": user_id}
