"""Router del Analista IA."""
import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..services import auth
from ..services.analista import consultar
from ..services import analista_memoria as memoria

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/analista", tags=["analista"])


class AnalistaIn(BaseModel):
    question: str


def _username(user: dict) -> str:
    return user.get("username") or user.get("sub") or ""


@router.post("")
def preguntar(
    payload: AnalistaIn,
    user: dict = Depends(auth.get_current_user),
) -> dict[str, str]:
    """
    Recibe una pregunta y devuelve la respuesta del Analista IA en lenguaje natural.
    Guarda el historial de la conversación por usuario.
    """
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="question vacío")
    try:
        respuesta = consultar(payload.question.strip(), username=_username(user))
        return {"output": respuesta}
    except Exception as e:
        logger.exception("Error en analista")
        raise HTTPException(status_code=500, detail=f"Analista IA: {e}")


@router.get("/historial")
def historial(user: dict = Depends(auth.get_current_user)) -> list[dict]:
    """Historial de conversación del usuario con el Analista (cronológico)."""
    return memoria.listar(_username(user))


@router.delete("/historial")
def borrar_historial(user: dict = Depends(auth.get_current_user)) -> dict:
    """Borra el historial de conversación del usuario."""
    n = memoria.borrar(_username(user))
    return {"borrados": n}


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "analista"}
