"""Modelo de chat con fallback de proveedor: Claude primario → OpenAI de reserva.

Porta el comportamiento de `services/agente_core/motor.py` (reintentos ante errores
transitorios y cambio de proveedor si el primario no responde), pero apoyado en
LangChain: `max_retries` cubre el reintento con backoff y `with_fallbacks` el cambio
de proveedor. Menos código propio que mantener y el mismo resultado observable.

El proveedor que efectivamente contestó se deduce del `response_metadata` del mensaje,
porque `with_fallbacks` no lo informa.
"""
from __future__ import annotations

import logging
from typing import Any, Sequence

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.tools import BaseTool

from ..config import settings
from ..obs import metrics

log = logging.getLogger("agents.llm")

# USD por millón de tokens (entrada, salida). Solo para estimar costo en agent_runs;
# si un modelo no está acá el costo queda en 0 y la métrica no miente, solo no cuenta.
_PRECIOS: dict[str, tuple[float, float]] = {
    "claude-haiku-4-5": (1.00, 5.00),
    "claude-sonnet-4": (3.00, 15.00),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4o-mini": (0.15, 0.60),
}


def _anthropic(**kwargs: Any) -> BaseChatModel:
    from langchain_anthropic import ChatAnthropic

    return ChatAnthropic(
        model=settings.ANTHROPIC_MODEL,
        api_key=settings.ANTHROPIC_API_KEY,
        timeout=settings.SONNER_LLM_TIMEOUT,
        max_retries=settings.SONNER_LLM_MAX_RETRIES,
        temperature=0,
        **kwargs,
    )


def _openai(**kwargs: Any) -> BaseChatModel:
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=settings.OPENAI_CHAT_MODEL,
        api_key=settings.OPENAI_API_KEY,
        timeout=settings.SONNER_LLM_TIMEOUT,
        max_retries=settings.SONNER_LLM_MAX_RETRIES,
        temperature=0,
        **kwargs,
    )


def construir(
    tools: Sequence[BaseTool] | None = None,
    *,
    max_tokens: int = 1200,
) -> BaseChatModel:
    """Modelo listo para invocar, con tools bindeadas y fallback de proveedor.

    Si falta una de las dos API keys se usa solo la que haya. Si no hay ninguna,
    `construir` falla acá y no en medio de una conversación.
    """
    primario = _anthropic(max_tokens=max_tokens) if settings.ANTHROPIC_API_KEY else None
    reserva = _openai(max_tokens=max_tokens) if settings.OPENAI_API_KEY else None
    if primario is None and reserva is None:
        raise RuntimeError("Ni ANTHROPIC_API_KEY ni OPENAI_API_KEY están configuradas")

    if tools:
        primario = primario.bind_tools(tools) if primario is not None else None
        reserva = reserva.bind_tools(tools) if reserva is not None else None

    if primario is None:
        return reserva  # type: ignore[return-value]
    if reserva is None:
        return primario
    return primario.with_fallbacks([reserva])


def _proveedor_de(modelo: str) -> str:
    m = (modelo or "").lower()
    if m.startswith("claude"):
        return "claude"
    if m.startswith(("gpt", "o1", "o3", "o4")):
        return "openai"
    return "desconocido"


def leer_uso(mensaje: AIMessage) -> dict[str, Any]:
    """Proveedor, modelo, tokens y costo estimado de una respuesta del LLM."""
    modelo = str(
        mensaje.response_metadata.get("model_name")
        or mensaje.response_metadata.get("model")
        or ""
    )
    proveedor = _proveedor_de(modelo)
    uso = mensaje.usage_metadata or {}
    tokens_in = int(uso.get("input_tokens") or 0)
    tokens_out = int(uso.get("output_tokens") or 0)

    precio = next((p for k, p in _PRECIOS.items() if modelo.startswith(k)), None)
    costo = (
        round(tokens_in / 1_000_000 * precio[0] + tokens_out / 1_000_000 * precio[1], 6)
        if precio else 0.0
    )

    metrics.LLM_LLAMADAS.labels(proveedor=proveedor, modelo=modelo or "?", resultado="ok").inc()
    if tokens_in:
        metrics.TOKENS.labels(proveedor=proveedor, tipo="in").inc(tokens_in)
    if tokens_out:
        metrics.TOKENS.labels(proveedor=proveedor, tipo="out").inc(tokens_out)
    if costo:
        metrics.COSTO.labels(proveedor=proveedor).inc(costo)
    if proveedor == "openai" and settings.ANTHROPIC_API_KEY:
        # Había Claude disponible y contestó OpenAI: el primario falló.
        metrics.LLM_FALLBACK.labels(de="claude", a="openai").inc()
        log.warning("respondió el proveedor de reserva (%s)", modelo)

    return {
        "proveedor": proveedor, "modelo": modelo,
        "tokens_in": tokens_in, "tokens_out": tokens_out, "costo_usd": costo,
    }
