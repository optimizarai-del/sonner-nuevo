"""
Lista de bloqueo — chequea la BD primero, luego Google Docs como fallback.
Compara últimos 5 dígitos (mismo criterio que el n8n original).
"""
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


def _ultimos5(valor: str) -> str:
    solo_digitos = "".join(c for c in str(valor) if c.isdigit())
    return solo_digitos[-5:] if len(solo_digitos) >= 5 else solo_digitos


async def esta_bloqueado(identifier: str, db: AsyncSession) -> bool:
    """
    Devuelve True si el identificador está en la tabla blocked_contacts.
    Compara los últimos 5 dígitos para tolerar variaciones de formato.
    """
    from ..models import BlockedContact

    sufijo = _ultimos5(identifier)
    if not sufijo:
        return False

    try:
        result = await db.execute(select(BlockedContact))
        todos = result.scalars().all()
        for contacto in todos:
            if _ultimos5(contacto.identifier) == sufijo:
                logger.info(f"'{identifier}' bloqueado (coincide con '{contacto.identifier}')")
                return True
    except Exception as e:
        logger.error(f"Error chequeando blocklist: {e}")

    return False
