"""Router del agente externo Tomi.

- `POST /api/agente/probar` — probar el agente por texto, sin tocar el historial.
- `POST /api/agente/n8n`    — el relay que llama n8n hoy (modo "relay" del grafo).
- `GET  /api/agente/diag`   — diagnóstico de las integraciones (Google, memoria).

Los dos primeros corren sobre el grafo de LangGraph (`agents/graphs/externo.py`). El
contrato de salida de `/n8n` es el mismo de siempre para que los nodos de n8n de abajo
(trocear, switch, CRM, CSM) no se toquen.

Auth: header `X-Memoria-Key` con MEMORIA_INTERNAL_KEY (reusa el secreto existente).
"""
import logging
from typing import Any, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from ..agents.graphs import externo as grafo_externo
from ..config import settings
from ..services.agente_externo import tools_google
from ..services.memoria import memoria as memoria_det

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
    """Corre el agente y devuelve {respuesta, comando, mensaje_comando, _meta}."""
    _auth(x_memoria_key)
    return grafo_externo.correr(
        modo="relay",
        canal="whatsapp",
        chat_id=body.telefono,
        mensaje=body.mensaje,
        nombre=body.nombre,
        tipo_cliente=body.tipo_cliente,
        reunion=body.reunion_cliente.model_dump() if body.reunion_cliente else None,
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
    contrato = grafo_externo.correr(
        modo="relay",
        canal="whatsapp",
        chat_id=body.telefono,
        mensaje=body.mensaje,
        nombre=body.nombre or body.telefono,
        tipo_cliente=body.tipo_cliente,
        reunion=body.reunion_cliente.model_dump() if body.reunion_cliente else None,
    )
    return {
        "output": {
            "respuesta": contrato.get("respuesta", ""),
            "comando": contrato.get("comando", "nada"),
            "mensaje_comando": contrato.get("mensaje_comando"),
        },
        "tipo_cliente": contrato.get("tipo_cliente"),  # para el nodo CSM de n8n
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
        out["calendario"] = tools_google.disponibilidad(fecha)
    except Exception as e:  # noqa: BLE001
        out["calendario"] = {"excepcion": str(e)}
    try:
        out["salones"] = tools_google.salon(salon, pax)
    except Exception as e:  # noqa: BLE001
        out["salones"] = {"excepcion": str(e)}
    try:
        m = memoria_det.consultar("parlantes", fuente="materiales")
        out["memoria"] = {"encontrado": m.get("encontrado"), "origen": m.get("origen"),
                          "respuesta": (m.get("respuesta") or "")[:300],
                          "meta": m.get("_meta")}
    except Exception as e:  # noqa: BLE001
        out["memoria"] = {"excepcion": str(e)}
    return out
