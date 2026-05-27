from __future__ import annotations

import pytest

from src.config import Settings


def test_default_values() -> None:
    s = Settings(
        _env_file=None,
        PLM_USERNAME="test_user",
        PLM_PASSWORD="test_pass",
    )
    assert s.PLM_BASE_URL == "https://piaplmp.piagad.com"
    assert s.SCRAPE_INTERVAL_PARTS == 5
    assert s.SCRAPE_INTERVAL_DOCUMENTS == 5
    assert s.SCRAPE_INTERVAL_MQ_ACS == 5
    assert s.TEAMS_WEBHOOK_URL is None
    assert s.DINGTALK_WEBHOOK_URL is None
    assert s.DATABASE_URL == "sqlite+aiosqlite:///./plm_dashboard.db"
    assert s.LOG_LEVEL == "INFO"
    assert s.RETENTION_DAYS == 90
    assert s.AI_PROVIDER == "ollama"
    assert s.AI_API_KEY is None
    assert s.AI_MODEL == "llama3"
    assert s.AI_ENABLED is True


def test_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PLM_BASE_URL", "https://custom.plm.com")
    monkeypatch.setenv("PLM_USERNAME", "override_user")
    monkeypatch.setenv("PLM_PASSWORD", "override_pass")
    monkeypatch.setenv("SCRAPE_INTERVAL_PARTS", "10")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg:///custom_db")
    monkeypatch.setenv("AI_PROVIDER", "openai")
    monkeypatch.setenv("AI_API_KEY", "sk-test-key")
    monkeypatch.setenv("AI_ENABLED", "false")

    s = Settings(_env_file=None)
    assert s.PLM_BASE_URL == "https://custom.plm.com"
    assert s.PLM_USERNAME == "override_user"
    assert s.PLM_PASSWORD == "override_pass"
    assert s.SCRAPE_INTERVAL_PARTS == 10
    assert s.DATABASE_URL == "postgresql+asyncpg:///custom_db"
    assert s.AI_PROVIDER == "openai"
    assert s.AI_API_KEY == "sk-test-key"
    assert s.AI_ENABLED is False


def test_teams_webhook_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEAMS_WEBHOOK_URL", "https://teams.webhook.url")
    monkeypatch.setenv("PLM_USERNAME", "test_user")
    monkeypatch.setenv("PLM_PASSWORD", "test_pass")

    s = Settings(_env_file=None)
    assert s.TEAMS_WEBHOOK_URL == "https://teams.webhook.url"


def test_dingtalk_webhook_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DINGTALK_WEBHOOK_URL", "https://dingtalk.webhook.url")
    monkeypatch.setenv("PLM_USERNAME", "test_user")
    monkeypatch.setenv("PLM_PASSWORD", "test_pass")

    s = Settings(_env_file=None)
    assert s.DINGTALK_WEBHOOK_URL == "https://dingtalk.webhook.url"


def test_retention_days_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RETENTION_DAYS", "180")
    monkeypatch.setenv("PLM_USERNAME", "test_user")
    monkeypatch.setenv("PLM_PASSWORD", "test_pass")

    s = Settings(_env_file=None)
    assert s.RETENTION_DAYS == 180


def test_log_level_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("PLM_USERNAME", "test_user")
    monkeypatch.setenv("PLM_PASSWORD", "test_pass")

    s = Settings(_env_file=None)
    assert s.LOG_LEVEL == "DEBUG"


def test_database_url_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PLM_USERNAME", "test_user")
    monkeypatch.setenv("PLM_PASSWORD", "test_pass")

    s = Settings(_env_file=None)
    assert s.DATABASE_URL == "sqlite+aiosqlite:///./plm_dashboard.db"


def test_validation_error_empty_username() -> None:
    with pytest.raises(ValueError, match="PLM_USERNAME must not be empty"):
        Settings(_env_file=None, PLM_USERNAME="", PLM_PASSWORD="test_pass")


def test_validation_error_empty_password() -> None:
    with pytest.raises(ValueError, match="PLM_PASSWORD must not be empty"):
        Settings(_env_file=None, PLM_USERNAME="test_user", PLM_PASSWORD="")


def test_validation_error_both_empty() -> None:
    with pytest.raises(ValueError):
        Settings(_env_file=None, PLM_USERNAME="", PLM_PASSWORD="")
