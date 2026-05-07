"""FastAPI app para Contratos Sonner."""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import contratos

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Sonner — Contratos API",
    version="1.0.0",
    description="Genera contratos vía Google Docs + PDF y los guarda en Supabase.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(contratos.router)


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "contratos-api", "status": "running"}


@app.on_event("startup")
def _on_startup() -> None:
    logger.info("Contratos API arrancada — CORS origins: %s", settings.cors_origins_list)
