import asyncio
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db, AsyncSessionLocal
from ..schemas import ChatRequest, ChatResponse
from ..core.redis_client import debounce_process
from ..agents.internal_agent import InternalAgent

router = APIRouter(prefix="/chat", tags=["chat"])

DEBOUNCE_SECONDS = 25


async def _process_and_store(session_id: str, messages: list[str]) -> None:
    combined = "\n".join(messages)
    async with AsyncSessionLocal() as db:
        agent = InternalAgent(session_key=session_id, channel="web")
        await agent.run(combined, db)


@router.post("/pagina", response_model=ChatResponse)
async def chat_pagina(req: ChatRequest, background_tasks: BackgroundTasks):
    """
    Reproduce el flujo n8n PAGINA:
    push → wait 25s → check last → process.
    Responde inmediatamente con status 'procesando'.
    El cliente debe hacer polling o usar WebSocket para obtener la respuesta.
    """
    redis_key = f"chat:web:{req.sessionId}"

    async def debounce_and_run():
        messages = await debounce_process(redis_key, req.message, DEBOUNCE_SECONDS)
        if messages is None:
            return  # mensaje superseded
        async with AsyncSessionLocal() as db:
            agent = InternalAgent(session_key=req.sessionId, channel="web")
            await agent.run("\n".join(messages), db)

    background_tasks.add_task(debounce_and_run)
    return ChatResponse(status="procesando")


@router.post("/pagina/sync", response_model=ChatResponse)
async def chat_pagina_sync(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    """
    Versión síncrona para uso desde la interfaz web con streaming manual.
    Procesa el mensaje directamente (sin debounce) y devuelve los mensajes.
    """
    agent = InternalAgent(session_key=req.sessionId, channel="web")
    result = await agent.run(req.message, db)
    return ChatResponse(status="ok", messages=result["messages"])
