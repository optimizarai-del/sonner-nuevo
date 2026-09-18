"""FastAPI app del backend de Sonner — contratos + analista IA."""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import obs
from .config import settings
from .routers import (
    contratos, analista, settings as settings_router, auth as auth_router,
    csm, memoria, agente_externo, agente_interno, wa_externo,
)

obs.logs.configurar()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Sonner — Backend",
    version="1.1.0",
    description="Contratos (Google Docs + PDF) y Analista IA con tools sobre Supabase.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth_router.router)
app.include_router(contratos.router)
app.include_router(analista.router)
app.include_router(settings_router.router)
app.include_router(csm.router)
app.include_router(memoria.router)
app.include_router(agente_externo.router)
app.include_router(agente_interno.router)
app.include_router(wa_externo.router)
obs.montar(app)  # /health, /health/ready, /health/deps, /metrics


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "sonner-backend", "status": "running"}


@app.on_event("startup")
def _on_startup() -> None:
    logger.info("Sonner backend arrancado — CORS origins: %s", settings.cors_origins_list)
