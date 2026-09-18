"""App STANDALONE del Agente Externo de SONNER (Tomi).

Servicio independiente de la plataforma: expone el webhook de WhatsApp (YCloud), el
relay que llama n8n, los healthchecks y las métricas. Reusa el mismo código del backend
principal pero se despliega y escala aparte.

Workers: con `REDIS_URL` configurada el debounce y el dedupe son distribuidos y se puede
correr con varios workers. Sin Redis, el estado es por proceso y hay que quedarse en uno
(el arranque avisa por log cuál de los dos casos es).

Arranque:
    uvicorn app.agente_main:app --host 0.0.0.0 --port 8000
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import obs
from .config import settings
from .routers import agente_externo, agente_interno, wa_externo

obs.logs.configurar()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="SONNER — Agente Externo (Tomi)",
    version="2.0.0",
    description="Agente de WhatsApp (YCloud) sobre LangGraph, independiente de la plataforma.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Memoria-Key"],
)

app.include_router(wa_externo.router)       # POST /api/wa/webhook  (YCloud)
app.include_router(agente_externo.router)   # POST /api/agente/{probar,n8n}
app.include_router(agente_interno.router)   # POST /api/agente/interno{,/web}
obs.montar(app)                             # /health, /health/ready, /health/deps, /metrics


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "sonner-agente-externo", "status": "running"}


@app.on_event("startup")
def _startup() -> None:
    from .agents.nodes import _redis
    from .jobs import scheduler

    distribuido = _redis.cliente() is not None
    logger.info(
        "Agente de SONNER arrancado",
        extra={
            "buffer_s": settings.WA_BUFFER_SECONDS,
            "modelo": settings.ANTHROPIC_MODEL,
            "estado_distribuido": distribuido,
            "workers_soportados": "varios" if distribuido else "1",
        },
    )
    scheduler.iniciar()


@app.on_event("shutdown")
def _shutdown() -> None:
    from .jobs import scheduler

    scheduler.detener()
