import asyncio
import os
import logging
import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.redis_client import debounce_process, get_automation_state, toggle_automation
from ..core.blocklist import esta_bloqueado
from ..database import AsyncSessionLocal, get_db
from ..agents.external_agent import ExternalAgent
from ..models import BlockedContact

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telegram-externo", tags=["telegram-externo"])

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN_EXTERNO", "")
WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
DEBOUNCE_SECONDS = 25


async def send_message(chat_id: int, text: str) -> None:
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{TELEGRAM_API}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
        )


async def process_externo_message(chat_id: int, text: str) -> None:
    # 1. Verificar si la automatización está activa
    activa = await get_automation_state()
    if not activa:
        logger.info(f"Automatización OFF — ignorando mensaje de {chat_id}")
        return

    # 2. Verificar si el chat_id está en la lista de bloqueo
    async with AsyncSessionLocal() as db:
        try:
            bloqueado = await esta_bloqueado(str(chat_id), db)
            if bloqueado:
                logger.info(f"chat_id {chat_id} bloqueado → ignorado")
                return
        except Exception as e:
            logger.warning(f"No se pudo verificar blocklist: {e} — continuando")

    # 3. Debounce + procesar
    redis_key = f"chat:telegram-externo:{chat_id}"
    messages = await debounce_process(redis_key, text, DEBOUNCE_SECONDS)
    if messages is None:
        return

    combined = "\n".join(messages)
    async with AsyncSessionLocal() as db:
        agent = ExternalAgent(session_key=str(chat_id), route="minorista")
        result = await agent.run(combined, db)

    for i, msg in enumerate(result["messages"]):
        await send_message(chat_id, msg)
        if i < len(result["messages"]) - 1:
            await asyncio.sleep(3)


@router.post("/webhook")
async def telegram_externo_webhook(request: Request, background_tasks: BackgroundTasks):
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

    if not text:
        return {"ok": True}

    background_tasks.add_task(process_externo_message, chat_id, text)
    return {"ok": True}


@router.get("/set-webhook")
async def set_webhook_externo(url: str):
    """Registra el webhook del bot externo en Telegram."""
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


# ── Toggle automatización ──────────────────────────────────────────────────────

@router.post("/toggle-automatizacion")
async def toggle_auto():
    nuevo_estado = await toggle_automation()
    return {"estado": nuevo_estado, "activa": nuevo_estado == "ON"}


@router.get("/automatizacion-estado")
async def get_auto_estado():
    activa = await get_automation_state()
    return {"estado": "ON" if activa else "OFF", "activa": activa}


# ── Lista de bloqueo ───────────────────────────────────────────────────────────

class BlockedContactIn(BaseModel):
    identifier: str
    label: str = ""


@router.get("/blocklist")
async def get_blocklist(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BlockedContact).order_by(BlockedContact.created_at.desc()))
    items = result.scalars().all()
    return [
        {"id": c.id, "identifier": c.identifier, "label": c.label, "created_at": c.created_at}
        for c in items
    ]


@router.post("/blocklist", status_code=201)
async def add_to_blocklist(body: BlockedContactIn, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(
        select(BlockedContact).where(BlockedContact.identifier == body.identifier.strip())
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="El identificador ya está bloqueado")
    contacto = BlockedContact(identifier=body.identifier.strip(), label=body.label.strip())
    db.add(contacto)
    await db.commit()
    await db.refresh(contacto)
    return {"id": contacto.id, "identifier": contacto.identifier, "label": contacto.label, "created_at": contacto.created_at}


@router.delete("/blocklist/{contact_id}", status_code=204)
async def remove_from_blocklist(contact_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BlockedContact).where(BlockedContact.id == contact_id))
    contacto = result.scalar_one_or_none()
    if not contacto:
        raise HTTPException(status_code=404, detail="No encontrado")
    await db.execute(delete(BlockedContact).where(BlockedContact.id == contact_id))
    await db.commit()
