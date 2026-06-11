"""Router de contratos: genera Doc + PDF + guarda en Supabase."""
import logging
from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..services import auth
from ..services.google_drive import generar_contrato
from ..services.supabase_client import insertar_contrato

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/contratos", tags=["contratos"])


# ── Schema del formulario ─────────────────────────────────────────────────────
class ContratoIn(BaseModel):
    nombre_prestatario:     str
    DNI_prestatario:        str
    domicilio_prestatario:  str
    lugar_evento:           str
    dia_evento:             str
    dia_finevento:          str = ""           # NUEVO
    hora_inicio:            str
    hora_fin:               str
    dias_para_pagar:        str
    valor_total_prestacion: int = Field(default=0, ge=0)
    equipamientos:          str
    monto_total_pesos:      int = Field(default=0, ge=0)
    monto_total_reserva:    int = Field(default=0, ge=0)
    saldo_a_cancelar:       int = Field(default=0, ge=0)
    dia_firma:              str
    mes_firma:              str
    año_firma:              str

    model_config = {"populate_by_name": True}


# ── Endpoints ─────────────────────────────────────────────────────────────────
@router.post("")
def crear_contrato(
    payload: ContratoIn,
    _user: dict = Depends(auth.require_role("admin")),
) -> dict[str, Any]:
    """
    Genera un contrato completo:
    - Copia template de Google Docs
    - Reemplaza placeholders
    - Exporta a PDF y lo guarda en la misma carpeta
    - Registra en Supabase
    Devuelve { doc_url, pdf_url }.
    """
    form = payload.model_dump(by_alias=True)
    try:
        urls = generar_contrato(form)
    except Exception as e:
        logger.exception("Error generando contrato en Google Drive")
        raise HTTPException(status_code=500, detail=f"Google Drive: {e}")

    try:
        insertar_contrato(form, urls)
    except Exception as e:
        # No fallamos: el contrato ya está en Drive
        logger.warning("No se pudo guardar en Supabase: %s", e)

    return urls


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "contratos-api"}
