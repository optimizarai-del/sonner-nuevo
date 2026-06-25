"""Router del sub-agente Memoria — vector store de SONNER.

Reemplaza el sub-agente n8n (Gemini + 4 vector stores). n8n lo llama por
HTTP Request en vez de instanciar un LLM por consulta → más rápido y barato.

Auth: header `X-Memoria-Key` con MEMORIA_INTERNAL_KEY (env). Vacía = abierto.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ..config import settings
from ..services.memoria import memoria as mem
from ..services.memoria import vectorstore as vs

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/memoria", tags=["memoria"])


def _auth(x_memoria_key: Optional[str]) -> None:
    key = settings.MEMORIA_INTERNAL_KEY
    if not key:
        return
    if x_memoria_key != key:
        raise HTTPException(status_code=401, detail="key inválida")


class MemoriaIn(BaseModel):
    mensaje: str = Field(..., description="Comando del Agente Principal, ej: 'buscar en materiales: parlantes'")
    k: Optional[int] = Field(default=None, description="Top-K chunks por fuente")


@router.post("")
def consultar(body: MemoriaIn, x_memoria_key: Optional[str] = Header(default=None)) -> dict:
    """Devuelve {origen, encontrado, respuesta} verbatim desde el vector store.

    Nunca tira 500 hacia n8n: ante error inesperado responde un contrato válido
    con encontrado:'no' para que el Agente Principal pueda seguir.
    """
    _auth(x_memoria_key)
    try:
        return mem.consultar(body.mensaje, k=body.k)
    except Exception as e:  # noqa: BLE001
        logger.exception("Memoria falló")
        return JSONResponse(status_code=200, content={
            "origen": "mixto", "encontrado": "no",
            "respuesta": f"Servicio de memoria temporalmente no disponible: {e}",
        })


@router.get("/fuentes")
def fuentes(x_memoria_key: Optional[str] = Header(default=None)) -> dict:
    """Debug: cuántos chunks hay por fuente en el vector store."""
    _auth(x_memoria_key)
    return {"fuentes": vs.conteo_por_fuente()}
