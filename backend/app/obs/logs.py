"""Logging estructurado en JSON con correlación por corrida.

Hoy los logs son texto plano: para reconstruir qué pasó en una conversación hay que
leer el stream de EasyPanel y adivinar qué línea corresponde a qué mensaje. Acá cada
línea sale como JSON con `run_id`, `chat_id` y `canal`, así se puede filtrar por corrida.

Los campos de correlación viven en `contextvars`, así que funcionan igual con asyncio
(cada request/corrida tiene su propio contexto) sin pasarlos por parámetro.
"""
from __future__ import annotations

import contextvars
import json
import logging
import sys
from contextlib import contextmanager
from typing import Any, Iterator

_run_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("run_id", default=None)
_chat_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("chat_id", default=None)
_canal: contextvars.ContextVar[str | None] = contextvars.ContextVar("canal", default=None)

# Atributos internos de LogRecord: todo lo que no esté acá es un campo extra del autor.
_ESTANDAR = frozenset(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {
    "message", "asctime", "taskName",
}


class FormatoJSON(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        datos: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "nivel": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for clave, var in (("run_id", _run_id), ("chat_id", _chat_id), ("canal", _canal)):
            valor = var.get()
            if valor:
                datos[clave] = valor
        for k, v in record.__dict__.items():
            if k not in _ESTANDAR and not k.startswith("_"):
                datos[k] = v
        if record.exc_info:
            datos["excepcion"] = self.formatException(record.exc_info)
        return json.dumps(datos, ensure_ascii=False, default=str)


def configurar(nivel: int = logging.INFO, json_output: bool = True) -> None:
    """Configura el logging del proceso. Idempotente.

    `force=True` + stdout: sin esto uvicorn ya configuró el root logger y el panel de
    logs de EasyPanel queda mudo.
    """
    formato: logging.Formatter = (
        FormatoJSON() if json_output
        else logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(formato)
    logging.basicConfig(level=nivel, handlers=[handler], force=True)
    # httpx loguea cada request a nivel INFO; con el agente eso es ruido puro.
    logging.getLogger("httpx").setLevel(logging.WARNING)


@contextmanager
def contexto(run_id: str, chat_id: str = "", canal: str = "") -> Iterator[None]:
    """Asocia run_id/chat_id/canal a todo lo que se loguee dentro del bloque."""
    tokens = [
        _run_id.set(run_id),
        _chat_id.set(chat_id or None),
        _canal.set(canal or None),
    ]
    try:
        yield
    finally:
        for var, token in zip((_run_id, _chat_id, _canal), tokens):
            var.reset(token)


def run_id_actual() -> str | None:
    return _run_id.get()
