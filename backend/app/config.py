"""Configuración cargada desde variables de entorno."""
import logging

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# Fallback solo para no romper despliegues existentes — definir JWT_SECRET en el entorno.
_DEFAULT_JWT_SECRET = "sonner_jwt_secret_change_in_production_2026_xyz_abc_123"


class Settings(BaseSettings):
    # ── Google ────────────────────────────────────────────────────────────────
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REFRESH_TOKEN: str
    GOOGLE_DRIVE_TEMPLATE_DOC_ID: str = "1tgcbcLZaVia4pC27C07B3Ew9D9cYOOHEb4H3qipXMms"
    GOOGLE_DRIVE_CONTRATOS_FOLDER_ID: str = "1CuOv1EDBskL5T3-kzT_cBYE6F9Gz4qnw"

    # ── Supabase ──────────────────────────────────────────────────────────────
    SUPABASE_URL: str = "https://wndfjicwzmsuxxcsnccl.supabase.co"
    SUPABASE_ANON_KEY: str
    # service_role key — saltea RLS, solo el backend la conoce
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    # ── Anthropic (Analista IA) ───────────────────────────────────────────────
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-haiku-4-5-20251001"

    # ── Análisis de CSM ───────────────────────────────────────────────────────
    # Key compartida para que n8n registre interacciones vía POST /api/csm/log
    # (header X-CSM-Key). Si queda vacía, el endpoint no exige key.
    CSM_INTERNAL_KEY: str = ""

    # ── OpenAI (embeddings del sub-agente de Memoria) ─────────────────────────
    # Los `documents` se embebieron con OpenAI (1536 dims). Para consultar el
    # vector store hay que embeber la query con el MISMO modelo.
    OPENAI_API_KEY: str = ""
    OPENAI_EMBED_MODEL: str = "text-embedding-3-small"
    # Chat de OpenAI usado como LLM de RESERVA del sub-agente Memoria.
    OPENAI_CHAT_MODEL: str = "gpt-4.1-mini"

    # ── Sub-agente Memoria (vector store) ─────────────────────────────────────
    # Key compartida para que n8n consulte vía POST /api/memoria (header X-Memoria-Key).
    MEMORIA_INTERNAL_KEY: str = ""
    MEMORIA_TOPK: int = 5
    MEMORIA_MIN_SIMILARITY: float = 0.30

    # ── Auth (JWT) ────────────────────────────────────────────────────────────
    JWT_SECRET: str = _DEFAULT_JWT_SECRET
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 8

    # ── CORS ──────────────────────────────────────────────────────────────────
    # Orígenes permitidos separados por coma
    CORS_ORIGINS: str = "https://sonner.optimizar-ia.com,http://localhost:5180,http://localhost:5173"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()

if settings.JWT_SECRET == _DEFAULT_JWT_SECRET:
    logger.warning(
        "SEGURIDAD: JWT_SECRET no está definido en el entorno — se está usando el "
        "secret por defecto. Configurá la variable de entorno JWT_SECRET en producción."
    )
