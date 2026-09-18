"""Healthchecks.

- `GET /health`        liveness. No toca dependencias: responde mientras el proceso viva.
- `GET /health/ready`  readiness. 503 si falta algo sin lo cual el agente no puede
                       atender. Es el que tiene que apuntar EasyPanel.
- `GET /health/deps`   detalle por dependencia con latencia, para diagnosticar.

Criticidad: Supabase y una key de LLM son críticas (sin eso no hay respuesta posible).
Redis y Google son degradables — sin Redis el debounce cae a memoria, sin Google las
tools de calendario/salones derivan a Gabriel, que es el comportamiento de hoy.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..config import settings

log = logging.getLogger("obs.health")
router = APIRouter(tags=["observabilidad"])


def _medir(fn) -> dict[str, Any]:
    inicio = time.monotonic()
    try:
        detalle = fn()
        estado = "ok"
    except Exception as e:  # noqa: BLE001
        detalle = f"{type(e).__name__}: {e}"
        estado = "error"
    return {
        "estado": estado,
        "latencia_ms": int((time.monotonic() - inicio) * 1000),
        "detalle": detalle,
    }


def _check_supabase() -> str:
    from ..services import credentials as creds_service

    sb = creds_service._admin()
    if sb is None:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY no configurada")
    sb.table("automatizacion_config").select("id").limit(1).execute()
    return "consulta ok"


def _check_redis() -> str:
    if not settings.REDIS_URL:
        return "sin configurar — debounce en memoria (requiere 1 worker)"
    import redis

    redis.Redis.from_url(settings.REDIS_URL, socket_timeout=3).ping()
    return "ping ok"


def _check_llm() -> str:
    disponibles = [
        n for n, k in (("anthropic", settings.ANTHROPIC_API_KEY),
                       ("openai", settings.OPENAI_API_KEY)) if k
    ]
    if not disponibles:
        raise RuntimeError("ni ANTHROPIC_API_KEY ni OPENAI_API_KEY configuradas")
    return "+".join(disponibles)


def _check_google() -> str:
    faltantes = [
        n for n, v in (("GOOGLE_AGENT_CLIENT_ID", settings.GOOGLE_AGENT_CLIENT_ID),
                       ("GOOGLE_AGENT_CLIENT_SECRET", settings.GOOGLE_AGENT_CLIENT_SECRET),
                       ("GOOGLE_AGENT_REFRESH_TOKEN", settings.GOOGLE_AGENT_REFRESH_TOKEN))
        if not v
    ]
    if faltantes:
        return "sin configurar (" + ", ".join(faltantes) + ") — tools degradan a handoff"
    return "credenciales presentes"


CRITICAS = {"supabase": _check_supabase, "llm": _check_llm}
DEGRADABLES = {"redis": _check_redis, "google": _check_google}


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
def ready() -> JSONResponse:
    chequeos = {nombre: _medir(fn) for nombre, fn in CRITICAS.items()}
    listo = all(c["estado"] == "ok" for c in chequeos.values())
    return JSONResponse(
        status_code=200 if listo else 503,
        content={"status": "ready" if listo else "not_ready", "chequeos": chequeos},
    )


@router.get("/health/deps")
def deps() -> dict[str, Any]:
    chequeos = {n: _medir(f) for n, f in {**CRITICAS, **DEGRADABLES}.items()}
    return {
        "criticas": {n: chequeos[n] for n in CRITICAS},
        "degradables": {n: chequeos[n] for n in DEGRADABLES},
    }
