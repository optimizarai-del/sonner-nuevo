"""Router de Análisis de CSM — registro y evaluación de respuestas del agente."""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel

from ..config import settings
from ..services import auth
from ..services import csm as csm_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/csm", tags=["csm"])


# ── Schemas ───────────────────────────────────────────────────────────────────
class CsmLogIn(BaseModel):
    mensaje_cliente: str
    respuesta_agente: Optional[str] = None
    canal: Optional[str] = None            # whatsapp | telegram | sandbox | mail
    tipo_cliente: Optional[str] = None     # minorista | mayorista
    agente: Optional[str] = None           # principal | calendario | salones
    wa_id: Optional[str] = None
    cliente_nombre: Optional[str] = None


class CsmReviewIn(BaseModel):
    rating: Optional[str] = None           # good | mejorable | bad
    respuesta_corregida: Optional[str] = None
    tags: Optional[list[str]] = None
    tipo_cliente: Optional[str] = None
    nota: Optional[str] = None


# ── Auth interna para que n8n registre sin token de usuario ───────────────────
def _auth_internal(x_csm_key: Optional[str]) -> None:
    key = settings.CSM_INTERNAL_KEY
    if not key:
        return  # sin key configurada => endpoint abierto (igual protegido por CORS/red)
    if x_csm_key != key:
        raise HTTPException(status_code=401, detail="key inválida")


# ── Endpoints ─────────────────────────────────────────────────────────────────
@router.post("/log")
def log_interaction(
    body: CsmLogIn,
    x_csm_key: Optional[str] = Header(default=None),
) -> dict:
    """Registra una interacción del agente como pendiente de revisión."""
    _auth_internal(x_csm_key)
    if not body.mensaje_cliente.strip():
        raise HTTPException(status_code=400, detail="mensaje_cliente vacío")
    try:
        row = csm_service.insert_log(body.model_dump())
        return {"ok": True, "item": row}
    except Exception as e:
        logger.exception("Error registrando interacción CSM")
        raise HTTPException(status_code=500, detail=f"CSM log: {e}")


@router.get("")
def list_feedback(
    status: Optional[str] = Query(None, description="pending | reviewed"),
    rating: Optional[str] = Query(None, description="good | mejorable | bad"),
    canal: Optional[str] = None,
    tipo_cliente: Optional[str] = Query(None, description="minorista | mayorista"),
    agente: Optional[str] = Query(None, description="principal | calendario | salones"),
    limit: int = Query(50, le=200),
    offset: int = 0,
    _user: dict = Depends(auth.get_current_user),
) -> list[dict]:
    return csm_service.list_items(
        status=status, rating=rating, canal=canal,
        tipo_cliente=tipo_cliente, agente=agente, limit=limit, offset=offset,
    )


@router.post("/{item_id}/review")
def review_feedback(
    item_id: int,
    body: CsmReviewIn,
    user: dict = Depends(auth.get_current_user),
) -> dict:
    """El admin/asesor puntúa y/o corrige una interacción."""
    try:
        row = csm_service.review(item_id, body.model_dump(), user.get("username", ""))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if row is None:
        raise HTTPException(status_code=404, detail="Interacción no encontrada")
    return row


@router.get("/stats")
def feedback_stats(_user: dict = Depends(auth.get_current_user)) -> dict:
    return csm_service.stats()


@router.get("/export")
def export_dataset(
    only_good: bool = Query(True, description="Solo pares aprobados (good o corregidos)"),
    _admin: dict = Depends(auth.require_role("admin")),
) -> dict:
    return csm_service.export_dataset(only_good=only_good)
