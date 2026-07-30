"""Webhook de WhatsApp (YCloud) para el agente externo Tomi.

YCloud POSTea acá cada mensaje entrante. Respondemos 200 al instante y procesamos en
background (el LLM tarda segundos; si no contestamos rápido, YCloud reintenta y duplica).

Configurar en YCloud el webhook apuntando a:  https://<backend>/api/wa/webhook
"""
import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from ..services.agente_externo import canal_ycloud, flujo

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/wa", tags=["agente-externo-wa"])


@router.post("/webhook")
async def webhook(request: Request) -> JSONResponse:
    raw = await request.body()
    firma = request.headers.get("ycloud-signature")
    if not canal_ycloud.verificar_firma(raw, firma):
        logger.warning("Firma YCloud inválida — rechazo")
        return JSONResponse(status_code=401, content={"error": "firma inválida"})

    try:
        body = await request.json()
    except Exception:
        body = {}

    inbound = canal_ycloud.parsear_inbound(body)
    if inbound and inbound.get("usuario"):
        # Fire-and-forget: no bloqueamos la respuesta del webhook.
        flujo.recibir_async(inbound)

    # Siempre 200 rápido (YCloud solo quiere el ack).
    return JSONResponse(status_code=200, content={"respuesta": "procesando"})
