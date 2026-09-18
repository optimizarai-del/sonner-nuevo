"""Carga de los system prompts de los agentes.

El prompt del agente EXTERNO sigue viviendo en `services/agente_externo/prompt.py`
junto a su archivo `prompt_v35.txt`: se reusa en vez de copiarse acá, porque duplicar
25k caracteres de prompt garantiza que las dos copias terminen divergiendo.

Este módulo carga el del agente INTERNO, que sí se portó a `interno_v1.md`.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

_DIR = Path(__file__).parent
_TZ_AR = timezone(timedelta(hours=-3))

# Comentario HTML de cabecera del .md: es para quien lea el archivo, no para el modelo.
_FIN_CABECERA = "-->"


@lru_cache(maxsize=4)
def _crudo(nombre: str) -> str:
    texto = (_DIR / f"{nombre}.md").read_text(encoding="utf-8")
    if texto.lstrip().startswith("<!--"):
        texto = texto.split(_FIN_CABECERA, 1)[-1]
    return texto.strip()


def ahora_ar() -> str:
    """'yyyy-MM-dd HH:mm' en hora de Argentina (mismo formato que usaba n8n)."""
    return datetime.now(_TZ_AR).strftime("%Y-%m-%d %H:%M")


def interno(contexto: dict[str, Any] | None = None) -> str:
    """System prompt del agente interno, con la fecha real inyectada.

    En n8n la fecha entraba por un nodo `Date & Time` previo al agente; acá se resuelve
    al armar el prompt. Sin esto el modelo calcula "mañana" contra su fecha de
    entrenamiento, que es el bug clásico de los agentes de agenda.
    """
    cola = f"\n\nFecha y hora actual: {ahora_ar()} (zona horaria de Argentina)"
    if contexto:
        cola += f"\nContexto: {json.dumps(contexto, ensure_ascii=False)}"
    return _crudo("interno_v1") + cola


def mensaje_interno(texto: str, usuario: str = "") -> str:
    """Envuelve el mensaje del equipo. Simple a propósito: no hay template heredado."""
    if usuario:
        return f"{texto}\n\n(mensaje de: {usuario})"
    return texto
