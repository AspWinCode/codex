from __future__ import annotations

import json
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://platform:CHANGE_ME@postgres:5432/platform"
    SYNC_DATABASE_URL: str = "postgresql://platform:CHANGE_ME@postgres:5432/platform"
    REDIS_URL: str = "redis://redis:6379/0"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ADMIN_LOGIN: str = "admin"
    ADMIN_PASSWORD: str
    JUDGER_INTERNAL_TOKEN: str
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"
    AUTO_CREATE_TABLES: bool = False
    # Email / SMTP settings (optional — leave blank to disable email)
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    SMTP_TLS: bool = True
    FRONTEND_URL: str = "http://localhost:3000"
    # GetCourse webhook secret (оставь пустым чтобы отключить проверку)
    GETCOURSE_WEBHOOK_SECRET: str = ""
    # Общий секрет для SSO-перехода ученика из tirskix.space (learning-portal) — НЕ SECRET_KEY.
    SSO_SHARED_SECRET: str = ""
    SSO_AUDIENCE: str = "kodex"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins(self) -> List[str]:
        raw = (self.CORS_ORIGINS or "").strip()
        if not raw:
            return []
        if raw.startswith("["):
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                return []
            if isinstance(parsed, list):
                return [str(origin).strip() for origin in parsed if str(origin).strip()]
            return []
        return [origin.strip() for origin in raw.split(",") if origin.strip()]


settings = Settings()