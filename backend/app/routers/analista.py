"""Router del Analista IA."""
import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..services import auth
from ..services.analista import consultar

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/analista", tags=["analista"])


class AnalistaIn(BaseModel):
    question: str


@router.post("")
def preguntar(
    payload: AnalistaIn,
    _user: dict = Depends(auth.get_current_user),
) -> dict[str, str]:
    """
    Recibe una pregunta y devuelve la respuesta del Analista IA en lenguaje natural.
    """
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="question vacío")
    try:
        respuesta = consultar(payload.question.strip())
        return {"output": respuesta}
    except Exception as e:
        logger.exception("Error en analista")
        raise HTTPException(status_code=500, detail=f"Analista IA: {e}")


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "analista"}
