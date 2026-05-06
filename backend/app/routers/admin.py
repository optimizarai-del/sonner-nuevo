import os
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import ConversationMessage, VectorDocument
from ..schemas import MemoryDocument, MemoryDocumentOut, ConversationOut, TokenResponse
from ..core.vector_store import insert, list_by_source
from ..security import create_access_token, get_current_user, verify_password

router = APIRouter(prefix="/admin", tags=["admin"])

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "change_me")


@router.post("/token", response_model=TokenResponse)
async def login(form: OAuth2PasswordRequestForm = Depends()):
    if form.username != ADMIN_USERNAME or form.password != ADMIN_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
        )
    token = create_access_token({"sub": form.username})
    return TokenResponse(access_token=token)


@router.get("/memoria", response_model=list[MemoryDocumentOut])
async def get_memoria(
    source: str = "eventos",
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    docs = await list_by_source(db, source)
    return docs


@router.post("/memoria", response_model=MemoryDocumentOut)
async def crear_memoria(
    doc: MemoryDocument,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    return await insert(db, content=doc.content, source=doc.source)


@router.delete("/memoria/{doc_id}")
async def eliminar_memoria(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    stmt = select(VectorDocument).where(VectorDocument.id == doc_id)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    await db.delete(doc)
    await db.commit()
    return {"status": "deleted"}


@router.get("/conversaciones", response_model=list[ConversationOut])
async def get_conversaciones(
    canal: str = "web",
    session_key: str = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    stmt = select(ConversationMessage).where(ConversationMessage.channel == canal)
    if session_key:
        stmt = stmt.where(ConversationMessage.session_key == session_key)
    stmt = stmt.order_by(desc(ConversationMessage.created_at)).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()
