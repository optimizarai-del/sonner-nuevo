import asyncio
import hashlib
import hmac
import logging
import os
import httpx
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

logger = logging.getLogger(__name__)

from ..core.redis_client import debounce_process
from ..database import AsyncSessionLocal
from ..agents.internal_agent import InternalAgent

router = APIRouter(prefix="/telegram", tags=["telegram"])

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN_INTERNO", "")
WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
DEBOUNCE_SECONDS = 15


async def send_message(chat_id: int, text: str) -> None:
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{TELEGRAM_API}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
        )


async def process_telegram_message(chat_id: int, text: str, first_name: str) -> None:
    logger.info(f"[INTERNO] Mensaje recibido de {chat_id}: {text[:50]}")
    redis_key = f"chat:telegram:{chat_id}"
    try:
        messages = await debounce_process(redis_key, text, DEBOUNCE_SECONDS)
    except Exception as e:
        logger.error(f"[INTERNO] Error en debounce: {e}")
        return
    if messages is None:
        logger.info(f"[INTERNO] Debounce: mensaje superseded para {chat_id}")
        return

    logger.info(f"[INTERNO] Debounce completado para {chat_id}, {len(messages)} mensajes")
    combined = "\n".join(messages)
    try:
        async with AsyncSessionLocal() as db:
            agent = InternalAgent(session_key=str(chat_id), channel="telegram")
            result = await agent.run(combined, db)
        logger.info(f"[INTERNO] Respuesta generada para {chat_id}: {result['respuesta'][:60]}")
    except Exception as e:
        logger.error(f"[INTERNO] Error en agente: {e}", exc_info=True)
        return

    for i, msg in enumerate(result["messages"]):
        await send_message(chat_id, msg)
        if i < len(result["messages"]) - 1:
            await asyncio.sleep(3)


@router.post("/webhook")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    # Validar secret si está configurado
    if WEBHOOK_SECRET:
        token_hash = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if token_hash != WEBHOOK_SECRET:
            raise HTTPException(status_code=403, detail="Unauthorized")

    body = await request.json()

    message = body.get("message") or body.get("edited_message")
    if not message:
        return {"ok": True}

    chat_id = message["chat"]["id"]
    text = message.get("text", "")
    first_name = message.get("from", {}).get("first_name", "")

    if not text:
        return {"ok": True}

    background_tasks.add_task(process_telegram_message, chat_id, text, first_name)
    return {"ok": True}


@router.get("/set-webhook")
async def set_webhook(url: str):
    """Helper para registrar el webhook de Telegram."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{TELEGRAM_API}/setWebhook",
            json={
                "url": url,
                "secret_token": WEBHOOK_SECRET,
                "allowed_updates": ["message"],
            },
        )
    return resp.json()
