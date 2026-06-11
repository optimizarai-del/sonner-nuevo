from datetime import date, timedelta
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from ..database import get_db
from ..models import Contrato
from ..schemas import ContratoRequest, ContratoResponse, ContratoOut
from ..core import google_drive as gd
from ..core.google_gmail import notify_contrato
from ..security import get_current_user
import os

router = APIRouter(prefix="/contratos", tags=["contratos"])

TEMPLATE_DOC_ID = os.getenv("GOOGLE_DRIVE_TEMPLATE_DOC_ID")
CONTRATOS_FOLDER_ID = os.getenv("GOOGLE_DRIVE_CONTRATOS_FOLDER_ID")


def _build_replacements(req: ContratoRequest) -> dict[str, str]:
    try:
        dia_postevento = (date.fromisoformat(req.dia_evento) + timedelta(days=1)).isoformat()
    except Exception:
        dia_postevento = req.dia_evento

    return {
        "(nombre_prestatario)": req.nombre_prestatario,
        "(DNI_prestatario)": req.DNI_prestatario,
        "(domicilio_prestatario)": req.domicilio_prestatario,
        "(lugar_evento)": req.lugar_evento,
        "(dia_evento)": req.dia_evento,
        "(hora_inicio)": req.hora_inicio,
        "(hora_fin)": req.hora_fin,
        "(dias_para_pagar)": req.dias_para_pagar,
        "(valor_total_prestacion)": f"$ {req.valor_total_prestacion:,}",
        "(monto_total_pesos)": f"$ {req.monto_total_pesos:,}",
        "(monto_total_reserva) ": f"$ {req.monto_total_reserva:,}",
        "(saldo_a_cancelar)": f"$ {req.saldo_a_cancelar:,}",
        "(dia_firma)": req.dia_firma,
        "(mes_firma)": req.mes_firma,
        "(año_firma)": req.año_firma,
        "(Equipamientos)": req.equipamientos,
        "(dia_postevento)": dia_postevento,
    }


@router.post("", response_model=ContratoResponse)
async def generar_contrato(
    req: ContratoRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    doc_name = f"contrato {req.nombre_prestatario} {req.dia_evento}"

    try:
        # 1. Copiar template
        copied = gd.copy_document(TEMPLATE_DOC_ID, doc_name, CONTRATOS_FOLDER_ID)
        doc_id = copied["id"]

        # 2. Reemplazar variables
        replacements = _build_replacements(req)
        gd.replace_text_in_doc(doc_id, replacements)

        # 3. Exportar como PDF
        pdf_bytes = gd.export_as_pdf(doc_id)

        # 4. Subir PDF
        pdf_file = gd.upload_pdf(pdf_bytes, doc_name, CONTRATOS_FOLDER_ID)
        pdf_id = pdf_file["id"]
        pdf_url = pdf_file.get("webContentLink", "")

        # 5. Hacer público
        gd.make_public(pdf_id)

        # 6. Eliminar copia del Doc (ya tenemos el PDF)
        gd.delete_file(doc_id)

        # 7. Guardar en BD
        contrato = Contrato(
            nombre_prestatario=req.nombre_prestatario,
            dni_prestatario=req.DNI_prestatario,
            domicilio_prestatario=req.domicilio_prestatario,
            lugar_evento=req.lugar_evento,
            dia_evento=req.dia_evento,
            hora_inicio=req.hora_inicio,
            hora_fin=req.hora_fin,
            valor_total_prestacion=req.valor_total_prestacion,
            pdf_drive_id=pdf_id,
            pdf_url=pdf_url,
        )
        db.add(contrato)
        await db.commit()
        await db.refresh(contrato)

        # 8. Notificar por email (background)
        background_tasks.add_task(notify_contrato, req.nombre_prestatario, pdf_url)

        return ContratoResponse(
            status="success",
            message=f"Link de archivo: {pdf_url}",
            pdf_url=pdf_url,
            contrato_id=contrato.id,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando contrato: {str(e)}")


@router.get("", response_model=list[ContratoOut])
async def listar_contratos(db: AsyncSession = Depends(get_db)):
    stmt = select(Contrato).order_by(desc(Contrato.created_at)).limit(100)
    result = await db.execute(stmt)
    return result.scalars().all()
