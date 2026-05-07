"""Configuración cargada desde variables de entorno."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Google ────────────────────────────────────────────────────────────────
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REFRESH_TOKEN: str
    GOOGLE_DRIVE_TEMPLATE_DOC_ID: str = "16TLMxsuWMaq71Hu3rl41dSxucm53zOXwhBkatFlhTHQ"
    GOOGLE_DRIVE_CONTRATOS_FOLDER_ID: str = "1CuOv1EDBskL5T3-kzT_cBYE6F9Gz4qnw"

    # ── Supabase ──────────────────────────────────────────────────────────────
    SUPABASE_URL: str = "https://wndfjicwzmsuxxcsnccl.supabase.co"
    SUPABASE_ANON_KEY: str

    # ── CORS ──────────────────────────────────────────────────────────────────
    # Orígenes permitidos separados por coma
    CORS_ORIGINS: str = "https://sonner.optimizar-ia.com,http://localhost:5180,http://localhost:5173"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
