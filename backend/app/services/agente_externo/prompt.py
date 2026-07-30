"""Carga y armado del system prompt del agente externo (Tomi v3.5).

El archivo `prompt_v35.txt` es la versión definitiva (misma que corría en n8n). Termina
con dos placeholders que en n8n se resolvían con expresiones:
    Fecha y hora actual: {{ ... currentDate }}
    Reunión del cliente: {{ ... reunion_cliente }}
Acá los cortamos y los rellenamos en runtime con la fecha real (zona AR) y el contexto
de reunión del cliente.

El mensaje del usuario se arma con el mismo template que espera el prompt:
    recibes el siguiente mensaje
    {texto}

    estas hablando con: {nombre}
    tipo de cliente: {minorista|mayorista}
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any

_DIR = os.path.dirname(__file__)
_PROMPT_PATH = os.path.join(_DIR, "prompt_v35.txt")

# Zona horaria de Argentina (UTC-3, sin DST).
_TZ_AR = timezone(timedelta(hours=-3))

# Marcadores donde empieza la cola de placeholders a recortar.
_CORTE = "Fecha y hora actual:"


def _base() -> str:
    with open(_PROMPT_PATH, encoding="utf-8") as fh:
        txt = fh.read()
    idx = txt.find(_CORTE)
    if idx != -1:
        txt = txt[:idx]
    return txt.rstrip()


def ahora_ar() -> str:
    """'yyyy-MM-dd HH:mm' en hora de Argentina (mismo formato que n8n)."""
    return datetime.now(_TZ_AR).strftime("%Y-%m-%d %H:%M")


def construir_system(reunion_cliente: dict[str, Any] | None = None, fecha_actual: str | None = None) -> str:
    """Arma el system prompt final con fecha y contexto de reunión."""
    reunion = reunion_cliente or {"tiene": False, "fecha_hora_texto": None, "titulo": None}
    fecha = fecha_actual or ahora_ar()
    cola = (
        f"\n\nFecha y hora actual: {fecha}"
        f"\nReunión del cliente: {json.dumps(reunion, ensure_ascii=False)}"
    )
    return _base() + cola


def construir_mensaje(texto: str, nombre: str, tipo_cliente: str = "minorista") -> str:
    """Envuelve el mensaje del cliente en el template que espera el prompt."""
    tipo = tipo_cliente if tipo_cliente in ("minorista", "mayorista") else "minorista"
    return (
        f"recibes el siguiente mensaje \n{texto}\n\n"
        f"estas hablando con: {nombre}\n"
        f"tipo de cliente: {tipo}"
    )
