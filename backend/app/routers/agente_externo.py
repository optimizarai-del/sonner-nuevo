"""Router del agente externo Tomi.

Por ahora expone SOLO el endpoint de prueba `POST /api/agente/probar`, que permite
testear el cerebro por texto (sin YCloud). El webhook real de WhatsApp se agrega en Fase 2.

Auth: header `X-Memoria-Key` con MEMORIA_INTERNAL_KEY (reusa el secreto existente).
"""
import logging
from typing import Any, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from ..config import settings
from ..services.agente_externo import orquestador

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/agente", tags=["agente-externo"])


def _auth(x_memoria_key: Optional[str]) -> None:
    key = settings.MEMORIA_INTERNAL_KEY
    if not key:
        return
    if x_memoria_key != key:
        raise HTTPException(status_code=401, detail="key inválida")


class ReunionCtx(BaseModel):
    tiene: bool = False
    fecha_hora_texto: Optional[str] = None
    titulo: Optional[str] = None


class ProbarIn(BaseModel):
    mensaje: str = Field(..., description="Mensaje del cliente (texto).")
    telefono: str = Field(default="+540000000000", description="Teléfono del cliente (session id).")
    nombre: str = Field(default="", description="Nombre del cliente (WhatsApp profile name).")
    tipo_cliente: str = Field(default="minorista", description="minorista | mayorista")
    reunion_cliente: Optional[ReunionCtx] = None
    persistir: bool = Field(default=False, description="Guardar el turno en external_chat_histories.")


@router.post("/probar")
def probar(body: ProbarIn, x_memoria_key: Optional[str] = Header(default=None)) -> dict[str, Any]:
    """Corre el cerebro del agente externo y devuelve {respuesta, comando, mensaje_comando, _meta}."""
    _auth(x_memoria_key)
    return orquestador.responder(
        texto=body.mensaje,
        telefono=body.telefono,
        nombre=body.nombre,
        tipo_cliente=body.tipo_cliente,
        reunion_cliente=body.reunion_cliente.model_dump() if body.reunion_cliente else None,
        persistir=body.persistir,
    )
