"""Observabilidad del agente: logs, corridas, métricas, alertas y healthchecks.

Se monta con `montar(app)`, que agrega los routers de /health y /metrics.
"""
from __future__ import annotations

from fastapi import FastAPI

from . import alertas, health, logs, metrics, runs

__all__ = ["alertas", "health", "logs", "metrics", "runs", "montar"]


def montar(app: FastAPI) -> None:
    app.include_router(health.router)
    from ..config import settings

    if settings.SONNER_METRICS_ENABLED:
        app.include_router(metrics.router)
