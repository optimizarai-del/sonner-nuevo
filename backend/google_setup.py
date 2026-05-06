"""
Script de setup OAuth2 de Google — correr UNA SOLA VEZ.

Pasos:
1. Ir a https://console.cloud.google.com
2. Crear un proyecto nuevo "Sonner"
3. Habilitar: Drive API, Docs API, Calendar API, Gmail API
4. Crear credenciales: OAuth 2.0 client ID (tipo "Desktop app")
5. Descargar el JSON y guardarlo como "google_client_secrets.json" en esta carpeta
6. Correr: python google_setup.py
7. Copiar los valores al .env
"""

import json
import os
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.send",
]

CLIENT_SECRETS_FILE = "google_client_secrets.json"


def main():
    if not os.path.exists(CLIENT_SECRETS_FILE):
        print(f"ERROR: No se encontró {CLIENT_SECRETS_FILE}")
        print("Descargalo desde Google Cloud Console → Credenciales → OAuth 2.0 Client IDs")
        return

    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
    creds = flow.run_local_server(port=0)

    with open(CLIENT_SECRETS_FILE) as f:
        client_config = json.load(f)

    client_id = client_config["installed"]["client_id"]
    client_secret = client_config["installed"]["client_secret"]
    refresh_token = creds.refresh_token

    print("\n✅ Autenticación exitosa. Copiá estos valores a tu .env:\n")
    print(f"GOOGLE_CLIENT_ID={client_id}")
    print(f"GOOGLE_CLIENT_SECRET={client_secret}")
    print(f"GOOGLE_REFRESH_TOKEN={refresh_token}")
    print("\nGuardando en google_credentials_output.txt también...")

    with open("google_credentials_output.txt", "w") as f:
        f.write(f"GOOGLE_CLIENT_ID={client_id}\n")
        f.write(f"GOOGLE_CLIENT_SECRET={client_secret}\n")
        f.write(f"GOOGLE_REFRESH_TOKEN={refresh_token}\n")

    print("✅ Guardado en google_credentials_output.txt")
    print("⚠️  No commitees este archivo a git.")


if __name__ == "__main__":
    main()
