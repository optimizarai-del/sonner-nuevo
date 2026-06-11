from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ContratoRequest(BaseModel):
    nombre_prestatario: str
    DNI_prestatario: str
    domicilio_prestatario: str
    lugar_evento: str
    dia_evento: str
    hora_inicio: str
    hora_fin: str
    dias_para_pagar: str
    valor_total_prestacion: int = Field(default=0, ge=0)
    equipamientos: str
    monto_total_pesos: int = Field(default=0, ge=0)
    monto_total_reserva: int = Field(default=0, ge=0)
    saldo_a_cancelar: int = Field(default=0, ge=0)
    dia_firma: str
    mes_firma: str
    año_firma: str


class ContratoResponse(BaseModel):
    status: str
    message: str
    pdf_url: Optional[str] = None
    contrato_id: Optional[int] = None


class ChatRequest(BaseModel):
    sessionId: str
    message: str


class ChatResponse(BaseModel):
    status: str
    messages: Optional[list[str]] = None


class MemoryDocument(BaseModel):
    content: str
    source: str  # eventos | informacion_interna | materiales


class MemoryDocumentOut(BaseModel):
    id: int
    content: str
    source: str
    created_at: datetime

    class Config:
        from_attributes = True


class ContratoOut(BaseModel):
    id: int
    nombre_prestatario: str
    lugar_evento: str
    dia_evento: str
    pdf_url: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationOut(BaseModel):
    id: int
    session_key: str
    channel: str
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
