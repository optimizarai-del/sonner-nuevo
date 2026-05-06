import os
import base64
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from .google_auth import get_credentials

NOTIFY_ADDRESS = os.getenv("GMAIL_NOTIFY_ADDRESS", "Gabrieldj88@gmail.com")


def _service():
    return build("gmail", "v1", credentials=get_credentials(), cache_discovery=False)


def send_email(to: str, subject: str, body: str) -> dict:
    msg = MIMEText(body)
    msg["to"] = to
    msg["subject"] = subject
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    return _service().users().messages().send(userId="me", body={"raw": raw}).execute()


def notify_contrato(nombre: str, pdf_url: str) -> dict:
    subject = f"Contrato {nombre} realizado"
    body = (
        f"Aquí tienes el link para poder acceder al contrato de {nombre}\n"
        f"Puedes descargarlo haciendo click aquí: {pdf_url}"
    )
    return send_email(NOTIFY_ADDRESS, subject, body)
