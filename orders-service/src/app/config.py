import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ORDERS_DB_USER: str         = os.getenv("ORDERS_DB_USER", "")
    ORDERS_DB_PASSWORD: str     = os.getenv("ORDERS_DB_PASSWORD", "")
    ORDERS_DB_NAME: str         = os.getenv("ORDERS_DB_NAME", "")
    ORDERS_DB_HOST: str         = os.getenv("ORDERS_DB_HOST", "")
    ORDERS_DB_PORT: int         = int(os.getenv("ORDERS_DB_PORT",  "5432"))

    RABBIT_USER: str            = os.getenv("RABBIT_USER", "")
    RABBIT_PASSWORD: str        = os.getenv("RABBIT_PASSWORD", "")
    RABBIT_HOST: str            = os.getenv("RABBIT_HOST", "")
    RABBIT_PORT: int            = int(os.getenv("RABBIT_PORT", "5672"))

    OUTBOX_POLL_INTERVAL: int       = int(os.getenv("OUTBOX_POLL_INTERVAL", "1"))
    RESULT_CONSUMER_PREFETCH: int   = int(os.getenv("RESULT_CONSUMER_PREFETCH", "10"))

settings = Settings()
