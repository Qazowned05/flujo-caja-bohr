from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    project_name: str = "Flujo de Caja"
    database_url: str = "postgresql+psycopg://flujo_caja:flujo_caja@localhost:5432/flujo_caja"
    secret_key: str = "change-this-development-secret"
    access_token_expire_minutes: int = 480
    backend_cors_origins: list[str] = ["http://localhost:5173"]
    profit_and_loss_enabled: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
