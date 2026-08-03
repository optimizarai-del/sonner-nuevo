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
from ..services.agente_externo import orquestador, tools_google, supabase_ops
from ..services.memoria import agente_memoria

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


class N8nIn(BaseModel):
    mensaje: str = Field(..., description="Mensaje del cliente (ya buffizado por n8n).")
    telefono: str = Field(..., description="Teléfono del cliente (usuario/session id).")
    nombre: str = Field(default="", description="Nombre del cliente (WhatsApp profile).")
    tipo_cliente: Optional[str] = Field(default=None, description="minorista|mayorista; si falta, lo calcula el agente.")
    reunion_cliente: Optional[ReunionCtx] = Field(default=None, description="Si falta, lo calcula el agente.")


@router.post("/n8n")
def desde_n8n(body: N8nIn, x_memoria_key: Optional[str] = Header(default=None)) -> dict[str, Any]:
    """Cerebro para n8n. n8n recibe/buffiza/envía; esto solo piensa.

    Devuelve {"output": {respuesta, comando, mensaje_comando}} — misma forma que el
    nodo AI Agent que reemplaza, así los nodos de abajo (trocear/switch/CRM/CSM) no cambian.
    Si tipo_cliente o reunion_cliente no vienen, los calcula el agente.
    """
    _auth(x_memoria_key)
    tipo = body.tipo_cliente or supabase_ops.tipo_cliente(body.telefono)
    reunion = body.reunion_cliente.model_dump() if body.reunion_cliente else supabase_ops.contexto_reunion(body.telefono)
    contrato = orquestador.responder(
        texto=body.mensaje,
        telefono=body.telefono,
        nombre=body.nombre or body.telefono,
        tipo_cliente=tipo,
        reunion_cliente=reunion,
        persistir=True,
    )
    return {
        "output": {
            "respuesta": contrato.get("respuesta", ""),
            "comando": contrato.get("comando", "nada"),
            "mensaje_comando": contrato.get("mensaje_comando"),
        },
        "tipo_cliente": tipo,  # para que el nodo CSM de n8n lo registre bien
    }


@router.get("/diag")
def diag(
    fecha: str = "2026-12-13",
    salon: str = "Royal",
    pax: int = 150,
    x_memoria_key: Optional[str] = Header(default=None),
) -> dict[str, Any]:
    """Diagnóstico de integraciones: llama directo a calendario (GCal), salones (Sheets)
    y memoria, y devuelve su salida cruda. Sirve para verificar credenciales sin depender
    de los logs. Cada bloque atrapa su propio error para no tumbar el resto.
    """
    _auth(x_memoria_key)
    out: dict[str, Any] = {}
    try:
        out["google_diag"] = tools_google.diagnostico_google()
    except Exception as e:  # noqa: BLE001
        out["google_diag"] = {"excepcion": str(e)}
    try:
        out["calendario"] = tools_google.verificar_disponibilidad(
            f"verificar disponibilidad evento {fecha}")
    except Exception as e:  # noqa: BLE001
        out["calendario"] = {"excepcion": str(e)}
    try:
        out["salones"] = tools_google.verificar_salon(
            f"verificar_salon: {salon} para {pax} personas")
    except Exception as e:  # noqa: BLE001
        out["salones"] = {"excepcion": str(e)}
    try:
        m = agente_memoria.responder("buscar en materiales: parlantes")
        out["memoria"] = {"encontrado": m.get("encontrado"), "origen": m.get("origen"),
                          "respuesta": (m.get("respuesta") or "")[:300],
                          "proveedor": (m.get("_meta") or {}).get("proveedor")}
    except Exception as e:  # noqa: BLE001
        out["memoria"] = {"excepcion": str(e)}
    return out
