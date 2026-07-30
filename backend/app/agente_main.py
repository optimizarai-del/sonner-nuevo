"""App STANDALONE del Agente Externo de SONNER (Tomi).

Servicio independiente de la plataforma: expone SOLO el webhook de WhatsApp (YCloud) y
el endpoint de prueba del agente. Reusa el mismo código (`app.services.agente_externo`)
que el backend principal, pero se despliega y escala aparte.

IMPORTANTE: correr con UN solo worker (`--workers 1`). El buffer/debounce de mensajes es
en memoria; con varios workers cada uno tendría su propio buffer y se romperían las
respuestas agrupadas. Ver Dockerfile.agente.

Arranque:
    uvicorn app.agente_main:app --host 0.0.0.0 --port 8000 --workers 1
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import agente_externo, wa_externo

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="SONNER — Agente Externo (Tomi)",
    version="1.0.0",
    description="Agente de WhatsApp (YCloud) independiente de la plataforma.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Memoria-Key"],
)

app.include_router(wa_externo.router)       # POST /api/wa/webhook  (YCloud)
app.include_router(agente_externo.router)   # POST /api/agente/probar (test)


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "sonner-agente-externo", "status": "running"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.on_event("startup")
def _startup() -> None:
    logger.info("Agente Externo (Tomi) arrancado — buffer=%.0fs, modelo=%s",
                settings.WA_BUFFER_SECONDS, settings.ANTHROPIC_MODEL)
