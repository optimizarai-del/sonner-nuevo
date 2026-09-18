"""Métricas Prometheus del agente.

Exporta en `GET /metrics`. Complementan a `agent_runs`: la tabla sirve para mirar UNA
conversación, las métricas para ver tendencias (latencia p95, tasa de handoff, costo).

Nota multi-worker: `prometheus_client` cuenta por proceso. Con más de un worker hay que
definir `PROMETHEUS_MULTIPROC_DIR` (un directorio compartido y escribible) o cada worker
reporta solo lo suyo. Si esa variable está definida, acá se usa el collector multiproceso.
"""
from __future__ import annotations

import os

from fastapi import APIRouter, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST, REGISTRY, Counter, Histogram, generate_latest,
)
from prometheus_client.core import CollectorRegistry

router = APIRouter(tags=["observabilidad"])

MENSAJES = Counter(
    "sonner_mensajes_total", "Mensajes entrantes recibidos", ["canal", "audiencia"]
)
RESPUESTAS = Counter(
    "sonner_respuestas_total",
    "Corridas terminadas por resultado",
    ["canal", "resultado"],  # ok | handoff | cortado | error
)
LATENCIA = Histogram(
    "sonner_latencia_segundos",
    "Latencia de la corrida completa del grafo",
    ["canal"],
    buckets=(0.5, 1, 2, 3, 5, 8, 13, 21, 34, 60),
)
LLM_LLAMADAS = Counter(
    "sonner_llm_llamadas_total", "Llamadas al LLM", ["proveedor", "modelo", "resultado"]
)
LLM_FALLBACK = Counter(
    "sonner_llm_fallback_total", "Veces que se cayó al proveedor de reserva", ["de", "a"]
)
TOOL_LLAMADAS = Counter(
    "sonner_tool_llamadas_total", "Llamadas a herramientas", ["tool", "resultado"]
)
TOKENS = Counter("sonner_tokens_total", "Tokens consumidos", ["proveedor", "tipo"])
COSTO = Counter("sonner_costo_usd_total", "Costo estimado acumulado", ["proveedor"])
DEBOUNCE_DESCARTADOS = Counter(
    "sonner_debounce_descartados_total",
    "Corridas abortadas porque llegó un mensaje más nuevo",
)
HANDOFFS = Counter("sonner_handoffs_total", "Derivaciones a humano", ["motivo"])
CORTES = Counter(
    "sonner_cortes_total", "Corridas cortadas antes del agente", ["motivo"]
)


def _registry() -> CollectorRegistry:
    """Registry multiproceso si está configurado; si no, el global del proceso."""
    directorio = os.environ.get("PROMETHEUS_MULTIPROC_DIR")
    if not directorio:
        return REGISTRY
    from prometheus_client import multiprocess

    reg = CollectorRegistry()
    multiprocess.MultiProcessCollector(reg)
    return reg


@router.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(_registry()), media_type=CONTENT_TYPE_LATEST)
