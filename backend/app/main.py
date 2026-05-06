from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pathlib import Path

# .env está en la raíz del proyecto (2 niveles arriba de app/main.py)
_env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(_env_path if _env_path.exists() else ".env")

from .database import create_tables
from .routers import contratos, chat_web, telegram_webhook, telegram_externo_webhook, whatsapp_webhook, admin, metrics, analyst


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    yield


app = FastAPI(title="Sonner API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(contratos.router)
app.include_router(chat_web.router)
app.include_router(telegram_webhook.router)
app.include_router(telegram_externo_webhook.router)
app.include_router(whatsapp_webhook.router)
app.include_router(admin.router)
app.include_router(metrics.router)
app.include_router(analyst.router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "sonner-api"}
