"""
Router de configuración: gestión de credenciales editables desde la UI.
GET  /api/settings        → lista todas (sin valores secretos)
PUT  /api/settings/{key}  → actualiza el valor
"""
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services import credentials

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/settings", tags=["settings"])


class UpdateValue(BaseModel):
    value: str


@router.get("")
def listar() -> dict:
    """Lista todas las credenciales con su metadata. NO devuelve valores secretos."""
    try:
        items = credentials.list_all()
        return {"items": items}
    except Exception as e:
        logger.exception("Error listando settings")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{key}")
def actualizar(key: str, payload: UpdateValue) -> dict:
    """Actualiza el valor de una credencial."""
    if not key or not key.replace("_", "").isalnum():
        raise HTTPException(status_code=400, detail="key inválida")
    try:
        credentials.set(key, payload.value)
        return {"status": "ok", "key": key}
    except Exception as e:
        logger.exception("Error actualizando settings %s", key)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/invalidate")
def invalidar() -> dict:
    """Limpia el cache para forzar relectura de Supabase."""
    credentials.invalidate()
    return {"status": "cache cleared"}
