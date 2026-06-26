"""Router del sub-agente Memoria — vector store de SONNER.

Reemplaza el sub-agente n8n (Gemini + 4 vector stores). n8n lo llama por
HTTP Request en vez de instanciar un LLM por consulta → más rápido y barato.

Auth: header `X-Memoria-Key` con MEMORIA_INTERNAL_KEY (env). Vacía = abierto.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ..config import settings
from ..services.memoria import memoria as mem
from ..services.memoria import agente_memoria as ag
from ..services.memoria import vectorstore as vs

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/memoria", tags=["memoria"])


def _auth(x_memoria_key: Optional[str]) -> None:
    key = settings.MEMORIA_INTERNAL_KEY
    if not key:
        return
    if x_memoria_key != key:
        raise HTTPException(status_code=401, detail="key inválida")


class HistMsg(BaseModel):
    role: str
    content: str


class MemoriaIn(BaseModel):
    mensaje: Optional[str] = Field(default=None, description="Comando del Agente Principal, ej: 'buscar en materiales: parlantes'")
    k: Optional[int] = Field(default=None, description="Top-K chunks por fuente")
    historial: Optional[list[HistMsg]] = None
    modo: str = Field(default="llm", description="'llm' (Claude→OpenAI→determinístico) | 'directo' (sin LLM)")
    max_iter: int = 4


@router.post("")
def consultar(
    body: Optional[MemoriaIn] = None,
    mensaje: Optional[str] = Query(default=None, description="Comando; alternativa al body para clientes que solo mandan query string (n8n toolHttpRequest)."),
    modo: Optional[str] = Query(default=None),
    x_memoria_key: Optional[str] = Header(default=None),
) -> dict:
    """Devuelve {origen, encontrado, respuesta} desde el vector store.

    El comando puede venir en el body JSON ({"mensaje": ...}) o como query param
    (?mensaje=...). Esto último es para n8n, que en toolHttpRequest solo reconoce
    los placeholders {..} dentro de la URL.

    modo='llm' (default): Claude redacta, OpenAI de reserva, y si ambos fallan
    cae al parser determinístico. modo='directo': solo el parser determinístico.

    Nunca tira 500 hacia n8n: ante error inesperado responde un contrato válido
    con encontrado:'no' para que el Agente Principal pueda seguir.
    """
    _auth(x_memoria_key)
    msg = (body.mensaje if body and body.mensaje else None) or mensaje or ""
    modo_final = (body.modo if body else None) or modo or "llm"
    k = body.k if body else None
    hist = [{"role": h.role, "content": h.content} for h in (body.historial or [])] if body else []
    max_iter = body.max_iter if body else 4
    try:
        if modo_final == "directo":
            return mem.consultar(msg, k=k)
        return ag.responder(msg, historial=hist, max_iter=max_iter)
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
