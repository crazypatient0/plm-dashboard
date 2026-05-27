"""Integration tests for the PLM Dashboard REST API.

All tests use mocked database sessions and scraper/scheduler components to
avoid real PLM connections.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from src.api.routes import get_db
from src.config import Settings, get_settings
from src.app_factory import configure_app
from src.models import Base, ScrapeLog, ScrapeRecord


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        PLM_USERNAME="test_user",
        PLM_PASSWORD="test_pass",
        PLM_BASE_URL="https://plm-test.example.com",
        DATABASE_URL="sqlite:///:memory:",
        TEAMS_WEBHOOK_URL=None,
        DINGTALK_WEBHOOK_URL=None,
        LOG_LEVEL="ERROR",
    )


@pytest.fixture
def test_db_session() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = Session(engine)
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def client(test_settings: Settings, test_db_session: Session) -> TestClient:
    """Create a TestClient with overridden database dependency.

    The scraper and scheduler are mocked to avoid real connections.
    """
    # Prevent the lifespan from creating real DB/PLM connections
    with (
        patch("src.app_factory.create_scraper_from_settings") as mock_create_scraper,
        patch("src.scheduler.SchedulerService.start"),
        patch("src.scheduler.SchedulerService.stop"),
    ):
        mock_scraper = MagicMock()
        mock_scraper.scrape_all.return_value = {}
        mock_create_scraper.return_value = mock_scraper

        app = configure_app(settings=test_settings)

        # Override dependencies with our test doubles
        def _override_get_db() -> Session:
            yield test_db_session

        def _override_get_settings() -> Settings:
            return test_settings

        app.dependency_overrides[get_db] = _override_get_db
        app.dependency_overrides[get_settings] = _override_get_settings

        with TestClient(app) as tc:
            yield tc


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class TestHealth:
    def test_health_returns_ok(self, client: TestClient) -> None:
        resp = client.get("/api/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["version"] == "0.1.0"
        assert "timestamp" in body

    def test_health_returns_json_content_type(self, client: TestClient) -> None:
        resp = client.get("/api/health")
        assert resp.headers["content-type"].startswith("application/json")


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------


class TestGetLatestRecords:
    def test_empty_data_type(self, client: TestClient) -> None:
        resp = client.get("/api/records/parts")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_records_newest_first(
        self, client: TestClient, test_db_session: Session
    ) -> None:
        now = datetime.now(UTC)
        test_db_session.add_all([
            ScrapeRecord(data_type="parts", raw_data={"n": 1}, scraped_at=now - timedelta(hours=2)),
            ScrapeRecord(data_type="parts", raw_data={"n": 2}, scraped_at=now - timedelta(hours=1)),
            ScrapeRecord(data_type="parts", raw_data={"n": 3}, scraped_at=now),
        ])
        test_db_session.commit()

        resp = client.get("/api/records/parts")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3
        assert data[0]["raw_data"]["n"] == 3
        assert data[2]["raw_data"]["n"] == 1

    def test_respects_limit(self, client: TestClient, test_db_session: Session) -> None:
        now = datetime.now(UTC)
        test_db_session.add_all([
            ScrapeRecord(data_type="parts", raw_data={"i": i}, scraped_at=now)
            for i in range(10)
        ])
        test_db_session.commit()

        resp = client.get("/api/records/parts?limit=3")
        assert resp.status_code == 200
        assert len(resp.json()) == 3

    def test_invalid_limit_returns_400(self, client: TestClient) -> None:
        resp = client.get("/api/records/parts?limit=0")
        assert resp.status_code == 422  # Pydantic validation


class TestGetRecordsByRange:
    def test_returns_records_in_window(
        self, client: TestClient, test_db_session: Session
    ) -> None:
        now = datetime.now(UTC)
        test_db_session.add(
            ScrapeRecord(data_type="parts", raw_data={"x": 1}, scraped_at=now)
        )
        test_db_session.commit()

        params = urlencode({
            "since": (now - timedelta(hours=1)).isoformat(),
            "until": (now + timedelta(hours=1)).isoformat(),
        })
        resp = client.get(f"/api/records/parts/range?{params}")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_bad_datetime_returns_400(self, client: TestClient) -> None:
        resp = client.get("/api/records/parts/range?since=not-a-date")
        assert resp.status_code == 400


class TestGetRecordsCount:
    def test_returns_count(self, client: TestClient, test_db_session: Session) -> None:
        now = datetime.now(UTC)
        test_db_session.add_all([
            ScrapeRecord(data_type="parts", raw_data={}, scraped_at=now) for _ in range(5)
        ])
        test_db_session.commit()

        resp = client.get("/api/records/parts/count")
        assert resp.status_code == 200
        assert resp.json() == {"data_type": "parts", "count": 5}

    def test_empty_data_type(self, client: TestClient) -> None:
        resp = client.get("/api/records/parts/count")
        assert resp.status_code == 200
        assert resp.json()["count"] == 0


class TestGetSummary:
    def test_returns_summary(self, client: TestClient, test_db_session: Session) -> None:
        now = datetime.now(UTC)
        test_db_session.add_all([
            ScrapeRecord(data_type="parts", raw_data={}, scraped_at=now - timedelta(hours=i))
            for i in range(3)
        ])
        test_db_session.commit()

        resp = client.get("/api/records/parts/summary")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 3
        assert body["latest_scraped_at"] is not None
        assert body["oldest_scraped_at"] is not None

    def test_empty_data_type(self, client: TestClient) -> None:
        resp = client.get("/api/records/parts/summary")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0


class TestSearchRecords:
    def test_finds_by_field(
        self, client: TestClient, test_db_session: Session
    ) -> None:
        now = datetime.now(UTC)
        test_db_session.add_all([
            ScrapeRecord(data_type="parts", raw_data={"part_no": "ABC-123"}, scraped_at=now),
            ScrapeRecord(data_type="parts", raw_data={"part_no": "DEF-456"}, scraped_at=now),
        ])
        test_db_session.commit()

        resp = client.get("/api/records/parts/search?field=part_no&value=ABC")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["raw_data"]["part_no"] == "ABC-123"

    def test_no_match_returns_empty(self, client: TestClient) -> None:
        resp = client.get("/api/records/parts/search?field=name&value=nonexistent")
        assert resp.status_code == 200
        assert resp.json() == []


class TestPruneRecords:
    def test_prunes_old_data(
        self, client: TestClient, test_db_session: Session
    ) -> None:
        now = datetime.now(UTC)
        test_db_session.add(
            ScrapeRecord(data_type="parts", raw_data={"old": True}, scraped_at=now - timedelta(days=60))
        )
        test_db_session.add(
            ScrapeRecord(data_type="parts", raw_data={"new": True}, scraped_at=now - timedelta(days=5))
        )
        test_db_session.add(
            ScrapeLog(data_type="parts", status="success", started_at=now - timedelta(days=60))
        )
        test_db_session.commit()

        resp = client.delete("/api/records/prune?retention_days=30")
        assert resp.status_code == 200
        body = resp.json()
        assert body["records_deleted"] == 1
        assert body["logs_deleted"] == 1


# ---------------------------------------------------------------------------
# Logs
# ---------------------------------------------------------------------------


class TestGetLogs:
    def test_returns_recent_logs(self, client: TestClient, test_db_session: Session) -> None:
        now = datetime.now(UTC)
        test_db_session.add_all([
            ScrapeLog(data_type="parts", status="success", started_at=now - timedelta(hours=i))
            for i in range(3)
        ])
        test_db_session.commit()

        resp = client.get("/api/logs")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3

    def test_filters_by_data_type(
        self, client: TestClient, test_db_session: Session
    ) -> None:
        now = datetime.now(UTC)
        test_db_session.add(
            ScrapeLog(data_type="parts", status="success", started_at=now)
        )
        test_db_session.add(
            ScrapeLog(data_type="documents", status="success", started_at=now)
        )
        test_db_session.commit()

        resp = client.get("/api/logs?data_type=parts")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_empty_database(self, client: TestClient) -> None:
        resp = client.get("/api/logs")
        assert resp.status_code == 200
        assert resp.json() == []


# ---------------------------------------------------------------------------
# Scraper
# ---------------------------------------------------------------------------


class TestRunScrape:
    def test_scrape_all(self, client: TestClient) -> None:
        # The scraper was configured as a mock in the client fixture
        resp = client.post("/api/scrape/run", json={})
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"

    def test_scrape_specific_type(self, client: TestClient) -> None:
        resp = client.post("/api/scrape/run", json={"data_type": "part"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

    def test_invalid_data_type(self, client: TestClient) -> None:
        resp = client.post("/api/scrape/run", json={"data_type": "invalid"})
        assert resp.status_code == 400

    def test_scrape_status(self, client: TestClient) -> None:
        resp = client.get("/api/scrape/status")
        assert resp.status_code == 200
        assert resp.json()["initialized"] is True


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------


class TestSchedulerStatus:
    def test_status_returns_running(self, client: TestClient) -> None:
        resp = client.get("/api/scheduler/status")
        assert resp.status_code == 200
        assert "running" in resp.json()

    def test_jobs_when_scheduler_not_available(self, client: TestClient) -> None:
        # Simulate scheduler not initialized by clearing app state
        client.app.state.scheduler = None
        resp = client.get("/api/scheduler/jobs")
        assert resp.status_code == 503


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------


class TestSendTestNotification:
    def test_teams_without_webhook(self, client: TestClient) -> None:
        resp = client.post(
            "/api/notifications/test",
            json={"channel": "teams", "title": "Test", "message": "Hello"},
        )
        assert resp.status_code == 400
        assert "not configured" in resp.json()["detail"].lower()

    def test_dingtalk_without_webhook(self, client: TestClient) -> None:
        resp = client.post(
            "/api/notifications/test",
            json={"channel": "dingtalk", "title": "Test", "message": "Hello"},
        )
        assert resp.status_code == 400
        assert "not configured" in resp.json()["detail"].lower()

    def test_unsupported_channel(self, client: TestClient) -> None:
        resp = client.post(
            "/api/notifications/test",
            json={"channel": "slack", "title": "Test", "message": "Hello"},
        )
        assert resp.status_code == 400
        assert "unsupported" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------


class TestCORS:
    def test_allows_known_origin(self, client: TestClient) -> None:
        resp = client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.status_code == 200
        assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"

    def test_rejects_unknown_origin(self, client: TestClient) -> None:
        resp = client.options(
            "/api/health",
            headers={
                "Origin": "https://evil-site.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        # CORS middleware rejects preflight for unknown origins
        assert resp.status_code == 400
        allow_origin = resp.headers.get("access-control-allow-origin")
        assert allow_origin is None or allow_origin != "https://evil-site.com"

    def test_allows_credentials_header(self, client: TestClient) -> None:
        resp = client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.headers.get("access-control-allow-credentials") == "true"


# ---------------------------------------------------------------------------
# Error handling — 404
# ---------------------------------------------------------------------------


class TestNotFound:
    def test_unknown_route_returns_404(self, client: TestClient) -> None:
        resp = client.get("/api/nonexistent")
        assert resp.status_code == 404

    def test_unknown_route_body_is_json(self, client: TestClient) -> None:
        resp = client.get("/api/nonexistent")
        assert resp.headers["content-type"].startswith("application/json")
