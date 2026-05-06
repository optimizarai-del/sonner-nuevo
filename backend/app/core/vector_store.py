from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import VectorDocument
from .embeddings import embed


async def search(db: AsyncSession, query: str, source: str, top_k: int = 8) -> list[dict]:
    try:
        query_embedding = embed(query)
        stmt = (
            select(VectorDocument)
            .where(VectorDocument.source == source)
            .order_by(VectorDocument.embedding.l2_distance(query_embedding))
            .limit(top_k)
        )
        result = await db.execute(stmt)
        docs = result.scalars().all()
        return [{"id": d.id, "content": d.content, "source": d.source} for d in docs]
    except Exception:
        # SQLite dev mode or empty DB — return no results
        return []


async def insert(db: AsyncSession, content: str, source: str, metadata: dict = None) -> VectorDocument:
    embedding = embed(content)
    doc = VectorDocument(
        content=content,
        embedding=embedding,
        source=source,
        metadata_=metadata or {},
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


async def list_by_source(db: AsyncSession, source: str, limit: int = 50) -> list[VectorDocument]:
    stmt = select(VectorDocument).where(VectorDocument.source == source).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()
