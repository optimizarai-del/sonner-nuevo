"""Router del agente interno de SONNER (equipo: Telegram y chat de la plataforma).

Reemplaza el cerebro de los workflows `AGT-INTERNO-SONNER` y `AGT-INTERNO-SONNER PAGINA`.
n8n conserva el trigger (Telegram / webhook), el debounce y el envío; acá se piensa.

    POST /api/agente/interno       canal Telegram — n8n envía la respuesta
    POST /api/agente/interno/web   chat de la plataforma — respuesta síncrona

Los dos devuelven `{"output": {respuesta, comando, contenido}}`, la misma forma que el
nodo AI Agent que reemplazan, así los nodos de abajo no se tocan. Además devuelven
`fragmentos` ya troceados: quien quiera puede saltearse el Code node de n8n.

Auth: header `X-Memoria-Key` con MEMORIA_INTERNAL_KEY.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from ..agents.graphs import interno as grafo_interno
from ..config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/agente/interno", tags=["agente-interno"])


def _auth(x_memoria_key: Optional[str]) -> None:
    key = settings.MEMORIA_INTERNAL_KEY
    if key and x_memoria_key != key:
        raise HTTPException(status_code=401, detail="key inválida")


class InternoIn(BaseModel):
    mensaje: str = Field(..., description="Mensaje del equipo (ya buffizado por n8n).")
    chat_id: str = Field(..., description="Chat de Telegram o sesión web.")
    nombre: str = Field(default="", description="Quién escribe.")
    persistir: bool = Field(default=True, description="False para probar sin tocar el historial.")


def _responder(body: InternoIn, canal: str) -> dict[str, Any]:
    salida = grafo_interno.correr(
        chat_id=body.chat_id, mensaje=body.mensaje, canal=canal,
        nombre=body.nombre, persistir=body.persistir,
    )
    return {
        "output": {
            "respuesta": salida.get("respuesta", ""),
            "comando": salida.get("comando", "nada"),
            "contenido": salida.get("contenido"),
        },
        "fragmentos": salida.get("fragmentos", []),
        "_meta": salida.get("_meta", {}),
    }


@router.post("")
def desde_telegram(body: InternoIn,
                   x_memoria_key: Optional[str] = Header(default=None)) -> dict[str, Any]:
    """Canal Telegram: la respuesta la manda n8n con su credencial del bot."""
    _auth(x_memoria_key)
    return _responder(body, canal="telegram")


@router.post("/web")
def desde_pagina(body: InternoIn,
                 x_memoria_key: Optional[str] = Header(default=None)) -> dict[str, Any]:
    """Chat de la plataforma: el webhook de n8n responde con esto mismo."""
    _auth(x_memoria_key)
    return _responder(body, canal="web")
