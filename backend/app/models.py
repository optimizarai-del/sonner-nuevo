from datetime import datetime
from sqlalchemy import String, Text, Integer, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from .database import Base


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_key: Mapped[str] = mapped_column(String(255), index=True)
    channel: Mapped[str] = mapped_column(String(50))  # web | telegram | whatsapp
    role: Mapped[str] = mapped_column(String(20))  # user | assistant
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class VectorDocument(Base):
    __tablename__ = "vector_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list] = mapped_column(Vector(1536))
    source: Mapped[str] = mapped_column(String(100), index=True)  # eventos | informacion_interna | materiales
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class BlockedContact(Base):
    __tablename__ = "blocked_contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    identifier: Mapped[str] = mapped_column(String(100), unique=True, index=True)  # Telegram ID o número
    label: Mapped[str] = mapped_column(String(255), nullable=True)  # Nombre/nota opcional
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Contrato(Base):
    __tablename__ = "contratos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre_prestatario: Mapped[str] = mapped_column(String(255))
    dni_prestatario: Mapped[str] = mapped_column(String(20))
    domicilio_prestatario: Mapped[str] = mapped_column(String(500))
    lugar_evento: Mapped[str] = mapped_column(String(255))
    dia_evento: Mapped[str] = mapped_column(String(20))
    hora_inicio: Mapped[str] = mapped_column(String(10))
    hora_fin: Mapped[str] = mapped_column(String(10))
    valor_total_prestacion: Mapped[int] = mapped_column(Integer)
    drive_doc_id: Mapped[str] = mapped_column(String(255), nullable=True)
    pdf_drive_id: Mapped[str] = mapped_column(String(255), nullable=True)
    pdf_url: Mapped[str] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
