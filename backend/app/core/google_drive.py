import os
import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from .google_auth import get_credentials

TEMPLATE_DOC_ID = os.getenv("GOOGLE_DRIVE_TEMPLATE_DOC_ID")
CONTRATOS_FOLDER_ID = os.getenv("GOOGLE_DRIVE_CONTRATOS_FOLDER_ID")


def _drive():
    return build("drive", "v3", credentials=get_credentials(), cache_discovery=False)


def _docs():
    return build("docs", "v1", credentials=get_credentials(), cache_discovery=False)


def copy_document(source_id: str, name: str, folder_id: str) -> dict:
    body = {"name": name, "parents": [folder_id]}
    return _drive().files().copy(fileId=source_id, body=body).execute()


def replace_text_in_doc(doc_id: str, replacements: dict[str, str]) -> dict:
    requests = [
        {
            "replaceAllText": {
                "containsText": {"text": placeholder, "matchCase": True},
                "replaceText": value,
            }
        }
        for placeholder, value in replacements.items()
    ]
    return _docs().documents().batchUpdate(documentId=doc_id, body={"requests": requests}).execute()


def export_as_pdf(file_id: str) -> bytes:
    request = _drive().files().export_media(fileId=file_id, mimeType="application/pdf")
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buf.getvalue()


def upload_pdf(pdf_bytes: bytes, name: str, folder_id: str) -> dict:
    buf = io.BytesIO(pdf_bytes)
    media = MediaIoBaseUpload(buf, mimetype="application/pdf", resumable=True)
    body = {"name": name, "parents": [folder_id], "mimeType": "application/pdf"}
    return _drive().files().create(body=body, media_body=media, fields="id,name,webContentLink,webViewLink").execute()


def make_public(file_id: str) -> None:
    _drive().permissions().create(
        fileId=file_id,
        body={"role": "reader", "type": "anyone"},
    ).execute()


def delete_file(file_id: str) -> None:
    _drive().files().delete(fileId=file_id).execute()
