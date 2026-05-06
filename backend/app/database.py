from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://sonner:sonner_pass@localhost:5432/sonner_db")
IS_SQLITE = DATABASE_URL.startswith("sqlite")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def create_tables():
    async with engine.begin() as conn:
        if not IS_SQLITE:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.run_sync(Base.metadata.create_all)
        else:
            # SQLite dev mode: skip vector_documents (no pgvector support)
            from .models import ConversationMessage, BlockedContact, Contrato
            non_vector_tables = [
                ConversationMessage.__table__,
                BlockedContact.__table__,
                Contrato.__table__,
            ]
            await conn.run_sync(
                lambda c: Base.metadata.create_all(c, tables=non_vector_tables)
            )
