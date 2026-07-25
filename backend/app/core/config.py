"""Application configuration.

All runtime configuration is read from environment variables (or a .env file)
exactly once, at import time, and exposed as a single immutable `settings`
object. Nothing else in the codebase reads os.environ directly.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # ---- app ---------------------------------------------------------------
    APP_NAME: str = "ULTRON AI Agent"
    APP_VERSION: str = "2.0.0"
    ENV: str = Field(default="development", description="development | production")
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    API_V1_PREFIX: str = "/api/v1"

    # ---- groq --------------------------------------------------------------
    GROQ_API_KEY: str = ""
    LLM_MODEL: str = "llama-3.3-70b-versatile"
    LLM_TEMPERATURE: float = 0.5
    LLM_MAX_TOKENS: int = 1024
    LLM_TIMEOUT_SECONDS: float = 30.0
    LLM_MAX_RETRIES: int = 2
    STT_MODEL: str = "whisper-large-v3-turbo"

    # ---- agent -------------------------------------------------------------
    AGENT_MAX_TOOL_STEPS: int = 5
    AGENT_TOOL_RESULT_CHAR_LIMIT: int = 6000
    AGENT_HISTORY_TURNS: int = 12

    # ---- storage -----------------------------------------------------------
    DB_PATH: Path = BASE_DIR / "ultron.db"
    WORKSPACE_DIR: Path = BASE_DIR / "workspace"
    MAX_UPLOAD_BYTES: int = 15 * 1024 * 1024  # 15 MB audio ceiling

    # ---- security ----------------------------------------------------------
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    API_KEY: str = ""  # when set, protected routes require X-API-Key
    RATE_LIMIT_REQUESTS: int = 60
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    # ---- feature flags (dangerous tools are opt-in) ------------------------
    ENABLE_CODE_EXECUTION: bool = False
    ENABLE_WEB_SEARCH: bool = True
    ENABLE_FILE_OPS: bool = True
    CODE_EXECUTION_TIMEOUT: int = 10
    CODE_EXECUTION_MEMORY_MB: int = 256

    @field_validator("ENV")
    @classmethod
    def _valid_env(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in {"development", "production", "test"}:
            raise ValueError("ENV must be development, production or test")
        return v

    @field_validator("LOG_LEVEL")
    @classmethod
    def _valid_log_level(cls, v: str) -> str:
        v = v.strip().upper()
        if v not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("LOG_LEVEL is not a valid logging level")
        return v

    # ---- derived -----------------------------------------------------------
    @property
    def cors_origin_list(self) -> list[str]:
        raw = self.CORS_ORIGINS.strip()
        if raw == "*":
            return ["*"]
        return [o.strip() for o in raw.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENV == "production"

    def check_runtime_requirements(self) -> list[str]:
        """Return a list of fatal misconfigurations. Empty list means OK."""
        problems: list[str] = []
        if not self.GROQ_API_KEY:
            problems.append(
                "GROQ_API_KEY is not set. Copy .env.example to .env and add your key."
            )
        if self.is_production:
            if "*" in self.cors_origin_list:
                problems.append("CORS_ORIGINS must not be '*' in production.")
            if not self.API_KEY:
                problems.append("API_KEY must be set in production.")
            if self.ENABLE_CODE_EXECUTION and not self.API_KEY:
                problems.append(
                    "ENABLE_CODE_EXECUTION requires API_KEY to be set."
                )
        return problems

    def prepare_directories(self) -> None:
        self.WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
        self.DB_PATH.parent.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

# The SpeechRecognition Groq backend reads the key from the process env.
if settings.GROQ_API_KEY:
    os.environ.setdefault("GROQ_API_KEY", settings.GROQ_API_KEY)
