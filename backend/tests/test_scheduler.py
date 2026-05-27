"""Tests for the APScheduler-based background scheduler.

All tests mock APScheduler to avoid real timer delays.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from src.config import Settings
from src.plm_client import PlmClient
from src.scheduler import (
    SchedulerService,
    ScrapeIntervalConfig,
    _safe_run_scrape_type,
    create_scraper_from_settings,
)
from src.scraper import Scraper, ScrapeResult


@pytest.fixture
def mock_scraper() -> MagicMock:
    """Create a mocked Scraper instance."""
    scraper = MagicMock(spec=Scraper)
    scraper._client = MagicMock(spec=PlmClient)
    scraper._db = MagicMock()
    scraper._scrape_single.return_value = ScrapeResult(
        data_type="part", records=[{"part_no": "TEST"}]
    )
    scraper._persist = MagicMock()
    scraper.scrape_all.return_value = {
        "part": ScrapeResult(data_type="part", records=[]),
        "document": ScrapeResult(data_type="document", records=[]),
        "conversion": ScrapeResult(data_type="conversion", records=[]),
    }
    return scraper


@pytest.fixture
def fast_config() -> ScrapeIntervalConfig:
    """Create a config with short intervals for testing."""
    return ScrapeIntervalConfig(
        base_interval_minutes=1,
        stagger_minutes=1,
        ai_analysis_hour=2,
        shutdown_timeout_seconds=1,
    )


@pytest.fixture
def mock_background_scheduler() -> MagicMock:
    """Create a mocked BackgroundScheduler."""
    scheduler = MagicMock()
    scheduler.running = False
    return scheduler


class TestScrapeIntervalConfig:
    """Tests for ScrapeIntervalConfig."""

    def test_default_values(self) -> None:
        """Default config should have sensible values."""
        config = ScrapeIntervalConfig()
        assert config.base_interval_minutes == 5
        assert config.stagger_minutes == 1
        assert config.ai_analysis_hour == 2
        assert config.shutdown_timeout_seconds == 30

    def test_stagger_offsets(self) -> None:
        """Stagger offsets should be 0, 1, 2 minutes for the three types."""
        config = ScrapeIntervalConfig(stagger_minutes=1)
        assert config.get_stagger_offset("part") == 0
        assert config.get_stagger_offset("document") == 1
        assert config.get_stagger_offset("conversion") == 2

    def test_stagger_offsets_with_custom_stagger(self) -> None:
        """Custom stagger_minutes should multiply the offsets."""
        config = ScrapeIntervalConfig(stagger_minutes=2)
        assert config.get_stagger_offset("part") == 0
        assert config.get_stagger_offset("document") == 2
        assert config.get_stagger_offset("conversion") == 4

    def test_from_settings_with_existing_attrs(self) -> None:
        """from_settings should read SCRAPE_INTERVAL_PARTS from existing config."""
        settings = Settings(
            PLM_USERNAME="test",
            PLM_PASSWORD="test",
            SCRAPE_INTERVAL_PARTS=10,
        )
        config = ScrapeIntervalConfig.from_settings(settings)
        assert config.base_interval_minutes == 10

    def test_from_settings_with_scrape_interval_minutes(self) -> None:
        """If SCRAPE_INTERVAL_MINUTES exists, prefer it over SCRAPE_INTERVAL_PARTS."""
        settings = SimpleNamespace(
            SCRAPE_INTERVAL_MINUTES=15,
            SCRAPE_INTERVAL_PARTS=5,
            AI_ANALYSIS_HOUR=2,
        )
        config = ScrapeIntervalConfig.from_settings(settings)  # type: ignore[arg-type]
        assert config.base_interval_minutes == 15

    def test_from_settings_ai_analysis_hour(self) -> None:
        """AI_ANALYSIS_HOUR should be read if present in settings."""
        settings = SimpleNamespace(
            SCRAPE_INTERVAL_PARTS=5,
            AI_ANALYSIS_HOUR=4,
        )
        config = ScrapeIntervalConfig.from_settings(settings)  # type: ignore[arg-type]
        assert config.ai_analysis_hour == 4


class TestSchedulerServiceJobRegistration:
    """Tests for job registration and configuration."""

    def test_registers_correct_number_of_jobs(
        self, mock_scraper: MagicMock, fast_config: ScrapeIntervalConfig
    ) -> None:
        """Scheduler should register 3 scrape jobs + 1 AI job = 4 total."""
        mock_scheduler = MagicMock()
        service = SchedulerService(
            scraper=mock_scraper,
            config=fast_config,
            scheduler=mock_scheduler,
        )

        service.start()

        assert mock_scheduler.add_job.call_count == 4

        job_ids = [call.kwargs.get("id") for call in mock_scheduler.add_job.call_args_list]
        assert "scrape.part" in job_ids
        assert "scrape.document" in job_ids
        assert "scrape.conversion" in job_ids
        assert "ai_analysis" in job_ids

    def test_scrape_jobs_have_interval_triggers(
        self, mock_scraper: MagicMock, fast_config: ScrapeIntervalConfig
    ) -> None:
        """Scrape jobs should use IntervalTrigger with correct interval."""
        mock_scheduler = MagicMock()
        service = SchedulerService(
            scraper=mock_scraper,
            config=fast_config,
            scheduler=mock_scheduler,
        )

        service.start()

        for call_args in mock_scheduler.add_job.call_args_list:
            job_id = call_args.kwargs.get("id")
            trigger = call_args.kwargs.get("trigger")

            if job_id and job_id.startswith("scrape."):
                assert isinstance(trigger, IntervalTrigger)
                assert trigger.interval == timedelta(minutes=fast_config.base_interval_minutes)

    def test_ai_analysis_has_cron_trigger(
        self, mock_scraper: MagicMock, fast_config: ScrapeIntervalConfig
    ) -> None:
        """AI analysis job should use CronTrigger at the configured hour."""
        mock_scheduler = MagicMock()
        config = ScrapeIntervalConfig(ai_analysis_hour=3)
        service = SchedulerService(
            scraper=mock_scraper,
            config=config,
            scheduler=mock_scheduler,
        )

        service.start()

        ai_calls = [
            c for c in mock_scheduler.add_job.call_args_list
            if c.kwargs.get("id") == "ai_analysis"
        ]
        assert len(ai_calls) == 1
        trigger = ai_calls[0].kwargs.get("trigger")
        assert isinstance(trigger, CronTrigger)

    def test_jobs_have_overlap_prevention(
        self, mock_scraper: MagicMock, fast_config: ScrapeIntervalConfig
    ) -> None:
        """All jobs should have coalesce=True and max_instances=1."""
        mock_scheduler = MagicMock()
        service = SchedulerService(
            scraper=mock_scraper,
            config=fast_config,
            scheduler=mock_scheduler,
        )

        service.start()

        for call_args in mock_scheduler.add_job.call_args_list:
            assert call_args.kwargs.get("coalesce") is True
            assert call_args.kwargs.get("max_instances") == 1


class TestSchedulerServiceStaggering:
    """Tests for staggered job start times."""

    def test_scrape_jobs_have_staggered_start_dates(
        self, mock_scraper: MagicMock
    ) -> None:
        """Scrape jobs should have start_date staggered by stagger_minutes."""
        mock_scheduler = MagicMock()
        config = ScrapeIntervalConfig(base_interval_minutes=5, stagger_minutes=1)
        service = SchedulerService(
            scraper=mock_scraper,
            config=config,
            scheduler=mock_scheduler,
        )

        service.start()

        jobs_by_type: dict[str, MagicMock] = {}
        for call_args in mock_scheduler.add_job.call_args_list:
            job_id = call_args.kwargs.get("id")
            if job_id and job_id.startswith("scrape."):
                job_type = job_id.replace("scrape.", "")
                jobs_by_type[job_type] = call_args

        assert "part" in jobs_by_type
        assert "document" in jobs_by_type
        assert "conversion" in jobs_by_type

        part_start = jobs_by_type["part"].kwargs["trigger"].start_date
        doc_start = jobs_by_type["document"].kwargs["trigger"].start_date
        mq_start = jobs_by_type["conversion"].kwargs["trigger"].start_date

        doc_offset = doc_start - part_start
        mq_offset = mq_start - part_start

        assert timedelta(seconds=55) < doc_offset < timedelta(seconds=65)
        assert timedelta(seconds=115) < mq_offset < timedelta(seconds=125)


class TestSchedulerServiceLifecycle:
    """Tests for start/stop/idempotency behavior."""

    def test_start_starts_scheduler(
        self, mock_scraper: MagicMock, fast_config: ScrapeIntervalConfig
    ) -> None:
        """start() should call scheduler.start()."""
        mock_scheduler = MagicMock()
        service = SchedulerService(
            scraper=mock_scraper,
            config=fast_config,
            scheduler=mock_scheduler,
        )

        assert service.is_running is False
        mock_scheduler.start.assert_not_called()

        service.start()

        assert service.is_running is True
        mock_scheduler.start.assert_called_once()

    def test_stop_stops_scheduler(
        self, mock_scraper: MagicMock, fast_config: ScrapeIntervalConfig
    ) -> None:
        """stop() should call scheduler.shutdown() with wait=True by default."""
        mock_scheduler = MagicMock()
        service = SchedulerService(
            scraper=mock_scraper,
            config=fast_config,
            scheduler=mock_scheduler,
        )

        service.start()
        mock_scheduler.shutdown.assert_not_called()

        service.stop()

        assert service.is_running is False
        mock_scheduler.shutdown.assert_called_once_with(wait=True)

    def test_stop_with_wait_false(
        self, mock_scraper: MagicMock, fast_config: ScrapeIntervalConfig
    ) -> None:
        """stop(wait=False) should pass wait=False to scheduler.shutdown()."""
        mock_scheduler = MagicMock()
        service = SchedulerService(
            scraper=mock_scraper,
            config=fast_config,
            scheduler=mock_scheduler,
        )

        service.start()
        service.stop(wait=False)

        mock_scheduler.shutdown.assert_called_once_with(wait=False)

    def test_start_idempotent(
        self, mock_scraper: MagicMock, fast_config: ScrapeIntervalConfig
    ) -> None:
        """Calling start() twice should be a no-op after the first call."""
        mock_scheduler = MagicMock()
        service = SchedulerService(
            scraper=mock_scraper,
            config=fast_config,
            scheduler=mock_scheduler,
        )

        service.start()
        first_start_count = mock_scheduler.start.call_count
        first_add_count = mock_scheduler.add_job.call_count

        service.start()

        assert mock_scheduler.start.call_count == first_start_count
        assert mock_scheduler.add_job.call_count == first_add_count
        assert service.is_running is True

    def test_stop_before_start_is_no_op(
        self, mock_scraper: MagicMock, fast_config: ScrapeIntervalConfig
    ) -> None:
        """Calling stop() before start() should be a no-op."""
        mock_scheduler = MagicMock()
        service = SchedulerService(
            scraper=mock_scraper,
            config=fast_config,
            scheduler=mock_scheduler,
        )

        assert service.is_running is False

        service.stop()

        mock_scheduler.shutdown.assert_not_called()
        assert service.is_running is False

    def test_get_jobs_returns_metadata(
        self, mock_scraper: MagicMock, fast_config: ScrapeIntervalConfig
    ) -> None:
        """get_jobs() should return formatted job metadata."""
        mock_scheduler = MagicMock()

        mock_job_1 = MagicMock()
        mock_job_1.id = "scrape.part"
        mock_job_1.trigger = IntervalTrigger(minutes=5)
        mock_job_1.next_run_time = datetime(2026, 5, 26, 12, 0, 0, tzinfo=UTC)

        mock_job_2 = MagicMock()
        mock_job_2.id = "ai_analysis"
        mock_job_2.trigger = CronTrigger(hour=2)
        mock_job_2.next_run_time = None

        mock_scheduler.get_jobs.return_value = [mock_job_1, mock_job_2]

        service = SchedulerService(
            scraper=mock_scraper,
            config=fast_config,
            scheduler=mock_scheduler,
        )

        jobs = service.get_jobs()

        assert len(jobs) == 2
        assert jobs[0]["id"] == "scrape.part"
        assert "interval" in jobs[0]["trigger"].lower()
        assert jobs[0]["next_run_time"] == "2026-05-26T12:00:00+00:00"

        assert jobs[1]["id"] == "ai_analysis"
        assert jobs[1]["next_run_time"] is None


class TestSafeRunScrapeType:
    """Tests for the _safe_run_scrape_type helper."""

    def test_calls_correct_scrape_method_for_part(self, mock_scraper: MagicMock) -> None:
        """For data_type='part', should call _scrape_single with _scrape_parts."""
        mock_scraper._scrape_single.return_value = ScrapeResult(
            data_type="part", records=[{"part_no": "P1"}]
        )

        result = _safe_run_scrape_type(mock_scraper, "part")

        mock_scraper._scrape_single.assert_called_once()
        call_args = mock_scraper._scrape_single.call_args
        assert call_args[0][0] == "part"
        assert result["part"].data_type == "part"

    def test_calls_persist_after_scrape(self, mock_scraper: MagicMock) -> None:
        """Should call _persist after _scrape_single."""
        scrape_result = ScrapeResult(data_type="document", records=[{"doc_no": "D1"}])
        mock_scraper._scrape_single.return_value = scrape_result

        _safe_run_scrape_type(mock_scraper, "document")

        mock_scraper._persist.assert_called_once_with(scrape_result)

    def test_handles_exceptions_gracefully(self, mock_scraper: MagicMock) -> None:
        """Exceptions should be caught and returned as error results."""
        mock_scraper._scrape_single.side_effect = ValueError("Something went wrong")

        result = _safe_run_scrape_type(mock_scraper, "conversion")

        assert "conversion" in result
        assert result["conversion"].error is not None
        assert "Something went wrong" in str(result["conversion"].error)


class TestJobOverlapPrevention:
    """Tests verifying that max_instances=1 prevents job overlap."""

    def test_max_instances_configured_correctly(
        self, mock_scraper: MagicMock, fast_config: ScrapeIntervalConfig
    ) -> None:
        """All jobs must have max_instances=1 to prevent overlaps."""
        mock_scheduler = MagicMock()
        service = SchedulerService(
            scraper=mock_scraper,
            config=fast_config,
            scheduler=mock_scheduler,
        )

        service.start()

        for call_args in mock_scheduler.add_job.call_args_list:
            assert call_args.kwargs.get("max_instances") == 1

    def test_coalesce_configured_correctly(
        self, mock_scraper: MagicMock, fast_config: ScrapeIntervalConfig
    ) -> None:
        """All jobs must have coalesce=True to skip stacked triggers."""
        mock_scheduler = MagicMock()
        service = SchedulerService(
            scraper=mock_scraper,
            config=fast_config,
            scheduler=mock_scheduler,
        )

        service.start()

        for call_args in mock_scheduler.add_job.call_args_list:
            assert call_args.kwargs.get("coalesce") is True


class TestAIAnalysisJob:
    """Tests for the AI analysis job placeholder."""

    def test_ai_analysis_job_registered(
        self, mock_scraper: MagicMock, fast_config: ScrapeIntervalConfig
    ) -> None:
        """AI analysis job should be registered with the scheduler."""
        mock_scheduler = MagicMock()
        service = SchedulerService(
            scraper=mock_scraper,
            config=fast_config,
            scheduler=mock_scheduler,
        )

        service.start()

        ai_calls = [
            c for c in mock_scheduler.add_job.call_args_list
            if c.kwargs.get("id") == "ai_analysis"
        ]
        assert len(ai_calls) == 1

    def test_ai_analysis_uses_cron_trigger(
        self, mock_scraper: MagicMock
    ) -> None:
        """AI analysis should use CronTrigger with the configured hour."""
        mock_scheduler = MagicMock()
        config = ScrapeIntervalConfig(ai_analysis_hour=5)
        service = SchedulerService(
            scraper=mock_scraper,
            config=config,
            scheduler=mock_scheduler,
        )

        service.start()

        ai_call = next(
            c for c in mock_scheduler.add_job.call_args_list
            if c.kwargs.get("id") == "ai_analysis"
        )
        trigger = ai_call.kwargs["trigger"]
        assert isinstance(trigger, CronTrigger)


class TestCreateScraperFromSettings:
    """Tests for the create_scraper_from_settings factory function."""

    def test_creates_scraper_instance(self) -> None:
        """Factory should return a Scraper instance."""
        settings = Settings(
            PLM_USERNAME="test_user",
            PLM_PASSWORD="test_pass",
            PLM_BASE_URL="https://example.com",
            DATABASE_URL="sqlite:///:memory:",
        )

        with patch("src.scheduler.create_engine") as mock_create_engine:
            with patch("src.scheduler.Session") as mock_session:
                with patch("src.scheduler.PlmClient") as mock_plm_client:
                    mock_engine = MagicMock()
                    mock_create_engine.return_value = mock_engine
                    mock_session_instance = MagicMock()
                    mock_session.return_value = mock_session_instance
                    mock_client_instance = MagicMock()
                    mock_plm_client.return_value = mock_client_instance

                    scraper = create_scraper_from_settings(settings)

                    assert isinstance(scraper, Scraper)
                    mock_create_engine.assert_called_once_with(settings.DATABASE_URL, echo=False)
                    mock_plm_client.assert_called_once_with(
                        base_url=settings.PLM_BASE_URL,
                        username=settings.PLM_USERNAME,
                        password=settings.PLM_PASSWORD,
                    )
