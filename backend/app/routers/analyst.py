import json
import os
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
import anthropic

from ..database import get_db
from ..models import ConversationMessage, Contrato, VectorDocument
from ..security import get_current_user

router = APIRouter(prefix="/analyst", tags=["analyst"])

_client = None


def _anthropic():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client


class AnalystRequest(BaseModel):
    question: str


async def _build_db_context(db: AsyncSession) -> str:
    """Construye un resumen de la BD para darle contexto al analista."""
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    total_msgs = (await db.execute(select(func.count()).select_from(ConversationMessage))).scalar()
    msgs_week = (await db.execute(
        select(func.count()).select_from(ConversationMessage)
        .where(ConversationMessage.created_at >= week_ago, ConversationMessage.role == "user")
    )).scalar()

    by_channel = (await db.execute(
        select(ConversationMessage.channel, func.count().label("n"))
        .where(ConversationMessage.role == "user")
        .group_by(ConversationMessage.channel)
    )).all()

    unique_sessions = (await db.execute(
        select(func.count(func.distinct(ConversationMessage.session_key)))
        .select_from(ConversationMessage)
    )).scalar()

    total_contratos = (await db.execute(select(func.count()).select_from(Contrato))).scalar()
    contratos_month = (await db.execute(
        select(func.count()).select_from(Contrato)
        .where(Contrato.created_at >= month_ago)
    )).scalar()

    # Últimos 20 mensajes de usuarios para contexto de temas
    last_msgs = (await db.execute(
        select(ConversationMessage.content, ConversationMessage.channel, ConversationMessage.created_at)
        .where(ConversationMessage.role == "user")
        .order_by(ConversationMessage.created_at.desc())
        .limit(30)
    )).all()

    # Últimos contratos
    last_contratos = (await db.execute(
        select(Contrato.nombre_prestatario, Contrato.lugar_evento, Contrato.dia_evento, Contrato.valor_total_prestacion)
        .order_by(Contrato.created_at.desc())
        .limit(10)
    )).all()

    context = f"""
=== DATOS DE LA BASE DE DATOS DE SONNER ===
Fecha de consulta: {now.strftime('%Y-%m-%d %H:%M')}

MENSAJES TOTALES: {total_msgs}
Mensajes de usuarios esta semana: {msgs_week}
Sesiones únicas: {unique_sessions}

MENSAJES POR CANAL:
{chr(10).join(f'  - {r.channel}: {r.n} mensajes de usuarios' for r in by_channel)}

CONTRATOS:
  - Total histórico: {total_contratos}
  - Último mes: {contratos_month}

ÚLTIMOS MENSAJES DE USUARIOS (muestra):
{chr(10).join(f'  [{r.channel}] {r.content[:150]}' for r in last_msgs)}

ÚLTIMOS CONTRATOS:
{chr(10).join(f'  - {r.nombre_prestatario} | {r.lugar_evento} | {r.dia_evento} | ${r.valor_total_prestacion:,}' for r in last_contratos)}
"""
    return context


ANALYST_SYSTEM = """Sos el Analista de Datos de SNR (Sonner).
Tenés acceso a datos reales de la base de datos de la empresa.
Tu trabajo es analizar estos datos y responder preguntas del equipo interno.

Sos directo, preciso y usás los datos que se te proveen.
Cuando los datos no son suficientes para responder con certeza, lo aclarás.
Respondés en español, de forma profesional y concisa.

No inventás datos que no estén en el contexto provisto."""


@router.post("/query")
async def analyst_query(
    req: AnalystRequest,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    context = await _build_db_context(db)
    prompt = f"{context}\n\n=== PREGUNTA DEL USUARIO ===\n{req.question}"

    response = _anthropic().messages.create(
        model="claude-sonnet-4-6",
        system=ANALYST_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2048,
    )

    answer = ""
    for block in response.content:
        if hasattr(block, "text"):
            answer = block.text
            break

    return {"answer": answer, "context_date": datetime.utcnow().isoformat()}
