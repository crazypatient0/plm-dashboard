from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    PLM_BASE_URL: str = "https://piaplmp.piagad.com"
    PLM_USERNAME: str = ""
    PLM_PASSWORD: str = ""
    SCRAPE_INTERVAL_PARTS: int = 1
    SCRAPE_INTERVAL_DOCUMENTS: int = 1
    SCRAPE_INTERVAL_MQ_ACS: int = 1
    TEAMS_WEBHOOK_URL: str | None = None
    DINGTALK_WEBHOOK_URL: str | None = None
    DATABASE_URL: str = "sqlite+aiosqlite:///./plm_dashboard.db"
    LOG_LEVEL: str = "INFO"
    RETENTION_DAYS: int = 90
    AI_PROVIDER: str = "ollama"
    AI_API_KEY: str | None = None
    AI_MODEL: str = "llama3"
    AI_ENABLED: bool = True


@lru_cache
def get_settings() -> Settings:
    """Get cached Settings instance."""
    return Settings()
