import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    PAYMENTS_DB_USER: str      = os.getenv("PAYMENTS_DB_USER", "")
    PAYMENTS_DB_PASSWORD: str  = os.getenv("PAYMENTS_DB_PASSWORD", "")
    PAYMENTS_DB_NAME: str      = os.getenv("PAYMENTS_DB_NAME", "")
    PAYMENTS_DB_HOST: str      = os.getenv("PAYMENTS_DB_HOST", "")
    PAYMENTS_DB_PORT: int      = int(os.getenv("PAYMENTS_DB_PORT", "5432"))

    RABBIT_USER: str           = os.getenv("RABBIT_USER", "")
    RABBIT_PASSWORD: str       = os.getenv("RABBIT_PASSWORD", "")
    RABBIT_HOST: str           = os.getenv("RABBIT_HOST", "")
    RABBIT_PORT: int           = int(os.getenv("RABBIT_PORT",  "5672"))

    OUTBOX_POLL_INTERVAL: int  = int(os.getenv("OUTBOX_POLL_INTERVAL", "1"))
    INBOX_PREFETCH_COUNT: int  = int(os.getenv("INBOX_PREFETCH_COUNT", "10"))

settings = Settings()
