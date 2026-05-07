"""
Servicio de Google Drive + Docs.
Hace lo que antes hacía n8n:
1. Copia template Google Doc
2. Reemplaza placeholders
3. Exporta como PDF
4. Sube el PDF a la misma carpeta
"""
import io
from typing import Any
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload

from ..config import settings


SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/documents",
]


def _credentials() -> Credentials:
    """Construye credenciales OAuth2 desde el refresh token."""
    return Credentials(
        token=None,
        refresh_token=settings.GOOGLE_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scopes=SCOPES,
    )


def _drive():
    return build("drive", "v3", credentials=_credentials(), cache_discovery=False)


def _docs():
    return build("docs", "v1", credentials=_credentials(), cache_discovery=False)


def generar_contrato(form: dict[str, Any]) -> dict[str, str]:
    """
    Genera un contrato a partir del template y los datos del formulario.
    Devuelve URLs públicas del Doc y del PDF.
    """
    drive = _drive()
    docs = _docs()

    nombre   = form["nombre_prestatario"]
    fecha    = form.get("dia_evento", "")
    base_name = f"Contrato {nombre} - {fecha}"

    # 1. Copiar template a la carpeta de contratos
    copia = drive.files().copy(
        fileId=settings.GOOGLE_DRIVE_TEMPLATE_DOC_ID,
        body={
            "name": base_name,
            "parents": [settings.GOOGLE_DRIVE_CONTRATOS_FOLDER_ID],
        },
        supportsAllDrives=True,
    ).execute()
    doc_id = copia["id"]

    # 2. Reemplazar placeholders.
    # El template usa paréntesis: (variable). Mayúsculas/minúsculas case-sensitive.
    placeholders = [
        "nombre_prestatario", "DNI_prestatario", "domicilio_prestatario",
        "lugar_evento", "dia_evento", "dia_finevento", "hora_inicio", "hora_fin",
        "dias_para_pagar", "valor_total_prestacion", "Equipamientos",
        "monto_total_pesos", "monto_total_reserva", "saldo_a_cancelar",
        "dia_firma", "mes_firma", "año_firma",
    ]
    # Aliases: el form puede traer las keys en otra capitalización
    aliases = {
        "Equipamientos":   ["Equipamientos", "equipamientos"],
        "DNI_prestatario": ["DNI_prestatario", "dni_prestatario"],
        "año_firma":       ["año_firma", "anio_firma", "ano_firma"],
    }
    money_keys = {"valor_total_prestacion", "monto_total_pesos",
                  "monto_total_reserva", "saldo_a_cancelar"}

    requests_body = []
    for key in placeholders:
        valor: Any = ""
        for alias in aliases.get(key, [key]):
            if alias in form and form[alias] not in (None, ""):
                valor = form[alias]
                break
        # Formato AR para montos
        if key in money_keys and isinstance(valor, (int, float)):
            valor = f"$ {int(valor):,}".replace(",", ".")
        requests_body.append({
            "replaceAllText": {
                "containsText": {"text": "(" + key + ")", "matchCase": True},
                "replaceText": str(valor),
            }
        })

    docs.documents().batchUpdate(
        documentId=doc_id,
        body={"requests": requests_body},
    ).execute()

    # 3. Exportar como PDF (descarga binaria)
    pdf_buffer = io.BytesIO()
    request = drive.files().export_media(fileId=doc_id, mimeType="application/pdf")
    downloader = MediaIoBaseDownload(pdf_buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    pdf_buffer.seek(0)

    # 4. Subir el PDF a la misma carpeta
    pdf_metadata = {
        "name": f"{base_name}.pdf",
        "parents": [settings.GOOGLE_DRIVE_CONTRATOS_FOLDER_ID],
    }
    media = MediaIoBaseUpload(pdf_buffer, mimetype="application/pdf", resumable=False)
    pdf_file = drive.files().create(
        body=pdf_metadata,
        media_body=media,
        fields="id",
        supportsAllDrives=True,
    ).execute()
    pdf_id = pdf_file["id"]

    return {
        "doc_url": f"https://docs.google.com/document/d/{doc_id}/edit",
        "pdf_url": f"https://drive.google.com/file/d/{pdf_id}/view",
        "doc_id":  doc_id,
        "pdf_id":  pdf_id,
    }
