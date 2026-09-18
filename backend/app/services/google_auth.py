"""Credenciales de Google del agente (Calendar + Sheets).

El agente usa un cliente OAuth propio (proyecto sonner-calendarios), distinto al de
contratos, porque necesita scopes de Calendar y Sheets que aquel no tiene.

Sobre los scopes: en el flujo de refresh token los permisos reales son los que se
otorgaron al generar el token, **no** los que se piden acá. La lista sirve de
documentación y de chequeo local; si el token se generó solo con permisos de lectura,
las operaciones de escritura del agente interno van a fallar con 403 aunque se pida
`SCOPES_ESCRITURA`. Regenerar el refresh token es un paso operativo (ver RUNBOOK).
"""
from __future__ import annotations

from google.oauth2.credentials import Credentials

from ..config import settings
from . import credentials as creds

SCOPES_LECTURA = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]
SCOPES_ESCRITURA = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/spreadsheets",
]


def credenciales(scopes: list[str] | None = None) -> Credentials:
    """Credenciales del agente. Cae a las de contratos si no hay token propio."""
    agent_rt = creds.get("GOOGLE_AGENT_REFRESH_TOKEN", settings.GOOGLE_AGENT_REFRESH_TOKEN)
    if agent_rt:
        refresh_token = agent_rt
        client_id = creds.get("GOOGLE_AGENT_CLIENT_ID", settings.GOOGLE_AGENT_CLIENT_ID) \
            or creds.get("GOOGLE_CLIENT_ID", settings.GOOGLE_CLIENT_ID)
        client_secret = creds.get("GOOGLE_AGENT_CLIENT_SECRET", settings.GOOGLE_AGENT_CLIENT_SECRET) \
            or creds.get("GOOGLE_CLIENT_SECRET", settings.GOOGLE_CLIENT_SECRET)
    else:
        # El token de contratos NO tiene scopes de Calendar/Sheets: va a fallar hasta
        # que se cargue GOOGLE_AGENT_REFRESH_TOKEN.
        refresh_token = creds.get("GOOGLE_REFRESH_TOKEN", settings.GOOGLE_REFRESH_TOKEN)
        client_id = creds.get("GOOGLE_CLIENT_ID", settings.GOOGLE_CLIENT_ID)
        client_secret = creds.get("GOOGLE_CLIENT_SECRET", settings.GOOGLE_CLIENT_SECRET)

    if not (refresh_token and client_id and client_secret):
        raise RuntimeError("Credenciales de Google incompletas")
    return Credentials(
        token=None, refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id, client_secret=client_secret,
        scopes=scopes or SCOPES_LECTURA,
    )
