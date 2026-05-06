from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import ConversationMessage, Contrato, VectorDocument
from ..security import get_current_user

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/overview")
async def overview(db: AsyncSession = Depends(get_db), _: dict = Depends(get_current_user)):
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    total_msgs = (await db.execute(select(func.count()).select_from(ConversationMessage))).scalar()
    msgs_week = (await db.execute(
        select(func.count()).select_from(ConversationMessage)
        .where(ConversationMessage.created_at >= week_ago)
    )).scalar()
    msgs_month = (await db.execute(
        select(func.count()).select_from(ConversationMessage)
        .where(ConversationMessage.created_at >= month_ago)
    )).scalar()

    by_channel = (await db.execute(
        select(ConversationMessage.channel, func.count().label("total"))
        .group_by(ConversationMessage.channel)
    )).all()

    user_msgs = (await db.execute(
        select(func.count()).select_from(ConversationMessage)
        .where(ConversationMessage.role == "user")
    )).scalar()

    unique_sessions = (await db.execute(
        select(func.count(func.distinct(ConversationMessage.session_key)))
        .select_from(ConversationMessage)
    )).scalar()

    total_contratos = (await db.execute(select(func.count()).select_from(Contrato))).scalar()
    contratos_month = (await db.execute(
        select(func.count()).select_from(Contrato)
        .where(Contrato.created_at >= month_ago)
    )).scalar()

    total_docs = (await db.execute(select(func.count()).select_from(VectorDocument))).scalar()
    docs_by_source = (await db.execute(
        select(VectorDocument.source, func.count().label("total"))
        .group_by(VectorDocument.source)
    )).all()

    return {
        "mensajes": {
            "total": total_msgs,
            "semana": msgs_week,
            "mes": msgs_month,
            "usuarios": user_msgs,
        },
        "sesiones": {"unicas": unique_sessions},
        "por_canal": [{"canal": r.channel, "total": r.total} for r in by_channel],
        "contratos": {"total": total_contratos, "mes": contratos_month},
        "memoria": {
            "total_docs": total_docs,
            "por_fuente": [{"fuente": r.source, "total": r.total} for r in docs_by_source],
        },
    }


@router.get("/mensajes-por-dia")
async def mensajes_por_dia(
    dias: int = 30,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    since = datetime.utcnow() - timedelta(days=dias)
    result = await db.execute(
        text("""
            SELECT
                DATE(created_at) AS dia,
                channel,
                COUNT(*) AS total
            FROM conversation_messages
            WHERE created_at >= :since AND role = 'user'
            GROUP BY DATE(created_at), channel
            ORDER BY dia ASC
        """),
        {"since": since},
    )
    rows = result.fetchall()
    return [{"dia": str(r.dia), "canal": r.channel, "total": r.total} for r in rows]


@router.get("/sesiones-activas")
async def sesiones_activas(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """Sesiones con actividad en las últimas 24h."""
    since = datetime.utcnow() - timedelta(hours=24)
    result = await db.execute(
        select(
            ConversationMessage.session_key,
            ConversationMessage.channel,
            func.count().label("mensajes"),
            func.max(ConversationMessage.created_at).label("ultimo"),
        )
        .where(ConversationMessage.created_at >= since)
        .group_by(ConversationMessage.session_key, ConversationMessage.channel)
        .order_by(func.max(ConversationMessage.created_at).desc())
        .limit(20)
    )
    rows = result.fetchall()
    return [
        {
            "session_key": r.session_key,
            "canal": r.channel,
            "mensajes": r.mensajes,
            "ultimo": r.ultimo.isoformat() if r.ultimo else None,
        }
        for r in rows
    ]


@router.get("/contratos-por-mes")
async def contratos_por_mes(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    result = await db.execute(
        text("""
            SELECT
                TO_CHAR(created_at, 'YYYY-MM') AS mes,
                COUNT(*) AS total
            FROM contratos
            GROUP BY TO_CHAR(created_at, 'YYYY-MM')
            ORDER BY mes ASC
        """)
    )
    rows = result.fetchall()
    return [{"mes": r.mes, "total": r.total} for r in rows]
