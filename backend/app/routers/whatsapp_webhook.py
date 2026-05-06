import asyncio
import os
import httpx
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from ..core.redis_client import debounce_process
from ..database import AsyncSessionLocal
from ..agents.external_agent import ExternalAgent

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])

VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
META_API = "https://graph.facebook.com/v19.0"
DEBOUNCE_SECONDS = 30


def _determine_route(phone_number: str, contact_name: str = "") -> str:
    """
    Determina si el contacto es Mayorista (C1) o Minorista (C2).
    Personalizar esta lógica según los datos de SONNER.
    Por defecto: minorista.
    Podés agregar una tabla de números mayoristas en BD.
    """
    return "minorista"


async def send_whatsapp_message(to: str, text: str) -> None:
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{META_API}/{PHONE_NUMBER_ID}/messages",
            headers={"Authorization": f"Bearer {ACCESS_TOKEN}"},
            json={
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to,
                "type": "text",
                "text": {"body": text},
            },
        )


async def process_whatsapp_message(phone: str, text: str, route: str) -> None:
    redis_key = f"chat:whatsapp:{phone}"
    messages = await debounce_process(redis_key, text, DEBOUNCE_SECONDS)
    if messages is None:
        return

    combined = "\n".join(messages)
    async with AsyncSessionLocal() as db:
        agent = ExternalAgent(session_key=phone, route=route)
        result = await agent.run(combined, db)

    for i, msg in enumerate(result["messages"]):
        await send_whatsapp_message(phone, msg)
        if i < len(result["messages"]) - 1:
            await asyncio.sleep(3)


@router.get("/webhook")
async def verify_webhook(request: Request):
    """Meta envía un GET para verificar el webhook al registrarlo."""
    params = dict(request.query_params)
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return int(challenge)

    raise HTTPException(status_code=403, detail="Verificación fallida")


@router.post("/webhook")
async def receive_message(request: Request, background_tasks: BackgroundTasks):
    """Meta envía un POST con cada mensaje entrante."""
    body = await request.json()

    try:
        entry = body["entry"][0]
        change = entry["changes"][0]
        value = change["value"]

        if "messages" not in value:
            return {"status": "no_message"}

        msg = value["messages"][0]
        phone = msg["from"]
        msg_type = msg.get("type", "")

        if msg_type != "text":
            return {"status": "non_text"}

        text = msg["text"]["body"]
        contact = value.get("contacts", [{}])[0].get("profile", {}).get("name", "")
        route = _determine_route(phone, contact)

        background_tasks.add_task(process_whatsapp_message, phone, text, route)

    except (KeyError, IndexError):
        pass

    return {"status": "ok"}
