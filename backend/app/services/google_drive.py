"""
Servicio de Google Drive + Docs.
Hace lo que antes hacía n8n:
1. Copia template Google Doc
2. Reemplaza placeholders
3. Exporta como PDF
4. Sube el PDF a la misma carpeta
"""
import io
import logging
from typing import Any
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload

from ..config import settings
from . import credentials as creds

logger = logging.getLogger("services.google_drive")


SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/documents",
]


def _credentials() -> Credentials:
    """Construye credenciales OAuth2 desde el refresh token (DB con fallback a env)."""
    refresh_token = creds.get("GOOGLE_REFRESH_TOKEN", settings.GOOGLE_REFRESH_TOKEN)
    client_id     = creds.get("GOOGLE_CLIENT_ID",     settings.GOOGLE_CLIENT_ID)
    client_secret = creds.get("GOOGLE_CLIENT_SECRET", settings.GOOGLE_CLIENT_SECRET)
    if not (refresh_token and client_id and client_secret):
        raise RuntimeError("Credenciales de Google incompletas — completalas en Configuración → Credenciales")
    return Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES,
    )


def _template_id() -> str:
    return creds.get("GOOGLE_DRIVE_TEMPLATE_DOC_ID", settings.GOOGLE_DRIVE_TEMPLATE_DOC_ID) or ""


def _folder_id() -> str:
    return creds.get("GOOGLE_DRIVE_CONTRATOS_FOLDER_ID", settings.GOOGLE_DRIVE_CONTRATOS_FOLDER_ID) or ""


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
        fileId=_template_id(),
        body={
            "name": base_name,
            "parents": [_folder_id()],
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
        "parents": [_folder_id()],
    }
    media = MediaIoBaseUpload(pdf_buffer, mimetype="application/pdf", resumable=False)
    pdf_file = drive.files().create(
        body=pdf_metadata,
        media_body=media,
        fields="id",
        supportsAllDrives=True,
    ).execute()
    pdf_id = pdf_file["id"]

    # 5. Compartir el PDF por link. El contrato se le manda al cliente, que no tiene
    #    acceso al Drive del estudio: sin esto el link que devolvemos no le abre.
    #    Es lo que hacía el nodo `Share file1` del workflow de n8n.
    #    OJO: "cualquiera con el link" incluye el DNI y el domicilio del prestatario.
    #    Solo se comparte el PDF, nunca el Doc editable.
    compartir_por_link(pdf_id)

    return {
        "doc_url": f"https://docs.google.com/document/d/{doc_id}/edit",
        "pdf_url": f"https://drive.google.com/file/d/{pdf_id}/view",
        "doc_id":  doc_id,
        "pdf_id":  pdf_id,
    }


def compartir_por_link(file_id: str) -> bool:
    """Da permiso de lectura a cualquiera con el link. Best-effort: el archivo ya existe."""
    try:
        _drive().permissions().create(
            fileId=file_id,
            body={"type": "anyone", "role": "reader"},
            supportsAllDrives=True,
        ).execute()
        return True
    except Exception as e:  # noqa: BLE001
        logger.warning("no se pudo compartir %s por link: %s", file_id, e)
        return False
