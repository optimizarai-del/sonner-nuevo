"""Entorno mínimo para los tests offline.

Las variables se definen ANTES de importar `app.config`, que valida al importarse
(JWT_SECRET sin valor hace fallar el arranque a propósito).

`SUPABASE_SERVICE_ROLE_KEY` queda vacía adrede: sin ella `credentials._admin()`
devuelve None y toda la capa de persistencia degrada sin tocar la red. Los tests de
esta carpeta no hacen ninguna llamada externa.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_DUMMY = {
    "JWT_SECRET": "test-secret-no-usar-en-produccion",
    "GOOGLE_CLIENT_ID": "test",
    "GOOGLE_CLIENT_SECRET": "test",
    "GOOGLE_REFRESH_TOKEN": "test",
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_ANON_KEY": "test",
    "SUPABASE_SERVICE_ROLE_KEY": "",
    "ANTHROPIC_API_KEY": "test",
    "OPENAI_API_KEY": "",
    "SONNER_ALERT_ENABLED": "false",
    "WA_BUFFER_SECONDS": "0",
}
for clave, valor in _DUMMY.items():
    os.environ.setdefault(clave, valor)

# El paquete `app` vive en backend/, un nivel arriba de tests/.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
