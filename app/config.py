from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Literal


class Settings(BaseSettings):
    database_url: str = Field(
        default="postgresql+asyncpg://user:password@localhost:5432/telegram_bot_host",
        alias="DATABASE_URL"
    )
    admin_secret_key: str = Field(
        default="change-this-to-a-very-long-secret-key",
        alias="ADMIN_SECRET_KEY"
    )
    admin_jwt_algorithm: str = Field(
        default="HS256",
        alias="ADMIN_JWT_ALGORITHM"
    )
    webhook_base_url: str = Field(
        default="https://your-domain.com",
        alias="WEBHOOK_BASE_URL"
    )
    webhook_path: str = Field(
        default="/webhook",
        alias="WEBHOOK_PATH"
    )
    host: str = Field(
        default="0.0.0.0",
        alias="HOST"
    )
    port: int = Field(
        default=8000,
        alias="PORT"
    )
    log_level: str = Field(
        default="info",
        alias="LOG_LEVEL"
    )
    polling_concurrent_bots: int = Field(
        default=10,
        alias="POLLING_CONCURRENT_BOTS"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()