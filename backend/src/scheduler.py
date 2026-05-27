"""APScheduler-based background job scheduler for PLM data scraping.

Orchestrates periodic scrape jobs with staggered start times and overlap
prevention. Integrates with FastAPI lifecycle events.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.config import Settings, get_settings
from src.plm_client import PlmClient

BJ_TZ = ZoneInfo("Asia/Shanghai")
from src.scraper import Scraper, ScrapeResult

logger = logging.getLogger(__name__)

DEFAULT_SCRAPE_INTERVAL_MINUTES = 5
DEFAULT_AI_ANALYSIS_HOUR = 2
DEFAULT_SHUTDOWN_TIMEOUT_SECONDS = 30

SCRAPE_JOB_TYPES: list[str] = ["part", "document", "conversion"]


@dataclass
class ScrapeIntervalConfig:
    """Configuration for scrape job intervals and staggering.

    Attributes:
        base_interval_minutes: Base interval between job executions.
        stagger_minutes: Offset between job types to prevent thundering herd.
            part:     base + 0 minutes
            document: base + 1 minute
            conversion:   base + 2 minutes
        ai_analysis_hour: Hour of day (0-23) for daily AI analysis job.
        shutdown_timeout_seconds: Maximum wait time for jobs during shutdown.
    """

    base_interval_minutes: int = DEFAULT_SCRAPE_INTERVAL_MINUTES
    stagger_minutes: int = 1
    ai_analysis_hour: int = DEFAULT_AI_ANALYSIS_HOUR
    shutdown_timeout_seconds: int = DEFAULT_SHUTDOWN_TIMEOUT_SECONDS

    @classmethod
    def from_settings(cls, settings: Settings) -> ScrapeIntervalConfig:
        """Create config from Settings instance with graceful attribute detection."""
        base_interval: int = DEFAULT_SCRAPE_INTERVAL_MINUTES
        ai_hour: int = DEFAULT_AI_ANALYSIS_HOUR

        if hasattr(settings, "SCRAPE_INTERVAL_MINUTES"):
            base_interval = int(settings.SCRAPE_INTERVAL_MINUTES)
        elif hasattr(settings, "SCRAPE_INTERVAL_PARTS"):
            base_interval = int(settings.SCRAPE_INTERVAL_PARTS)

        if hasattr(settings, "AI_ANALYSIS_HOUR"):
            ai_hour = int(settings.AI_ANALYSIS_HOUR)

        return cls(
            base_interval_minutes=base_interval,
            ai_analysis_hour=ai_hour,
        )

    def get_stagger_offset(self, job_type: str) -> int:
        """Get the stagger offset in minutes for a given job type."""
        offsets: dict[str, int] = {
            "part": 0,
            "document": 1,
            "conversion": 2,
        }
        return offsets.get(job_type, 0) * self.stagger_minutes


def _format_bj_time(dt) -> str | None:
    """Format a datetime as ISO string with explicit +08:00 timezone suffix."""
    if dt is None:
        return None
    iso = dt.isoformat()
    if dt.tzinfo is not None:
        return iso
    return f"{iso}+08:00"


def _safe_run_scrape_type(
    scraper: Scraper,
    data_type: str,
) -> dict[str, ScrapeResult]:
    """Safely run a single scrape type without propagating exceptions.

    Returns a dict with a single ScrapeResult entry for consistency with
    Scraper.scrape_all(), which is called when data_type is None.
    """
    try:
        if data_type == "part":
            result = scraper._scrape_single("part", scraper._scrape_parts)
            scraper._persist(result)
            return {"part": result}
        elif data_type == "document":
            result = scraper._scrape_single("document", scraper._scrape_documents)
            scraper._persist(result)
            return {"document": result}
        elif data_type == "conversion":
            result = scraper._scrape_single("conversion", scraper._scrape_conversion)
            scraper._persist(result)
            return {"conversion": result}
        else:
            return scraper.scrape_all()
    except Exception as e:
        logger.error("Scrape job failed for type '%s': %s", data_type, e, exc_info=True)
        error_result = ScrapeResult(data_type=data_type, error=str(e))
        return {data_type: error_result}


def create_scraper_from_settings(settings: Settings | None = None) -> Scraper:
    """Factory function to create a fully-configured Scraper from settings.

    Creates:
        - SQLAlchemy engine from DATABASE_URL
        - Session factory and session
        - PlmClient with PLM credentials
        - Scraper instance wired to both

    Note: The caller is responsible for closing the session and PlmClient
    when finished. For long-running jobs, consider creating a fresh Scraper
    per job invocation to avoid stale connections.

    Returns:
        Configured Scraper instance ready for scrape_all() calls.
    """
    if settings is None:
        settings = get_settings()

    # Convert async database URL to sync equivalent for scraper (same as in app factory)
    sync_url = settings.DATABASE_URL.replace("sqlite+aiosqlite://", "sqlite://")
    engine = create_engine(sync_url, echo=False)
    session_factory = sessionmaker(bind=engine)
    session = Session(engine)

    client = PlmClient(
        base_url=settings.PLM_BASE_URL,
        username=settings.PLM_USERNAME,
        password=settings.PLM_PASSWORD,
    )

    scraper = Scraper(client=client, db=session)

    scraper._engine = engine
    scraper._session_factory = session_factory

    return scraper


class SchedulerService:
    """APScheduler-based background job scheduler for PLM scraping.

    Manages periodic scrape jobs for parts, documents, and MQ ACS data,
    plus a daily AI analysis job. Features:

    - Staggered start times to avoid thundering herd
    - Overlap prevention via coalesce=True, max_instances=1
    - Graceful shutdown with configurable timeout
    - FastAPI lifecycle-compatible start/stop methods

    Usage::

        scheduler = SchedulerService(scraper, config)
        scheduler.start()  # on app startup
        # ... app runs ...
        scheduler.stop()   # on app shutdown
    """

    def __init__(
        self,
        scraper: Scraper,
        config: ScrapeIntervalConfig | None = None,
        scheduler: BackgroundScheduler | None = None,
    ) -> None:
        """Initialize the scheduler service.

        Args:
            scraper: Configured Scraper instance for executing scrapes.
            config: Interval and timing configuration. Uses defaults if None.
            scheduler: Optional BackgroundScheduler instance for testing/mocking.
        """
        self._scraper = scraper
        self._config = config or ScrapeIntervalConfig()
        self._scheduler = scheduler or BackgroundScheduler()
        self._running = False
        self._job_ids: set[str] = set()

    @property
    def is_running(self) -> bool:
        """Return True if the scheduler is currently running."""
        return self._running

    def start(self) -> None:
        """Start the scheduler and register all jobs.

        Idempotent: calling start() on an already-running scheduler logs
        a warning and returns without adding duplicate jobs.

        Jobs registered:
            scrape.part     - IntervalTrigger, staggered offset 0min
            scrape.document - IntervalTrigger, staggered offset 1min
            scrape.conversion   - IntervalTrigger, staggered offset 2min
            ai_analysis     - CronTrigger, daily at config.ai_analysis_hour
        """
        if self._running:
            logger.warning("Scheduler already running; start() is a no-op")
            return

        self._register_jobs()
        self._scheduler.start()
        self._running = True
        logger.info(
            "Scheduler started: %d scrape jobs + 1 AI analysis job",
            len(SCRAPE_JOB_TYPES),
        )

    def stop(self, wait: bool = True) -> None:
        """Stop the scheduler gracefully.

        Args:
            wait: If True, wait up to shutdown_timeout_seconds for running
                jobs to complete before shutting down. If False, shut down
                immediately without waiting.

        No-op if the scheduler is not running.
        """
        if not self._running:
            logger.debug("Scheduler not running; stop() is a no-op")
            return

        timeout = self._config.shutdown_timeout_seconds if wait else 0
        logger.info("Scheduler stopping (wait=%s, timeout=%ds)", wait, timeout)

        self._scheduler.shutdown(wait=wait)
        self._running = False
        self._job_ids.clear()
        logger.info("Scheduler stopped")

    def get_jobs(self) -> list[dict]:
        """Return metadata about currently registered jobs.

        Returns:
            List of dicts with 'id', 'trigger', and 'next_run_time' keys.
        """
        jobs = self._scheduler.get_jobs()
        return [
            {
                "id": job.id,
                "trigger": str(job.trigger),
                "next_run_time": (
                    _format_bj_time(job.next_run_time) if job.next_run_time else None
                ),
            }
            for job in jobs
        ]

    def _register_jobs(self) -> None:
        """Register all periodic jobs with the scheduler.

        Uses:
        - coalesce=True: If multiple triggers fire while a job is running,
          run it only once when the job becomes available.
        - max_instances=1: Never allow more than one concurrent instance
          of the same job.
        """
        for job_type in SCRAPE_JOB_TYPES:
            self._register_scrape_job(job_type)

        self._register_ai_analysis_job()

    def _register_scrape_job(self, job_type: str) -> None:
        """Register a single scrape job with staggered start time."""
        job_id = f"scrape.{job_type}"
        stagger_offset = self._config.get_stagger_offset(job_type)

        start_date = datetime.now(BJ_TZ) + timedelta(minutes=stagger_offset)

        trigger = IntervalTrigger(
            minutes=self._config.base_interval_minutes,
            start_date=start_date,
        )

        self._scheduler.add_job(
            self._scrape_job_wrapper,
            trigger=trigger,
            id=job_id,
            name=f"Scrape {job_type}",
            coalesce=True,
            max_instances=1,
            kwargs={"data_type": job_type},
        )

        self._job_ids.add(job_id)
        logger.info(
            "Registered scrape job '%s': interval=%dmin, stagger=%dmin",
            job_type,
            self._config.base_interval_minutes,
            stagger_offset,
        )

    def _register_ai_analysis_job(self) -> None:
        """Register the daily AI analysis job.

        Runs once per day at the configured hour (default 02:00 UTC).
        """
        job_id = "ai_analysis"

        trigger = CronTrigger(
            hour=self._config.ai_analysis_hour,
            minute=0,
        )

        self._scheduler.add_job(
            self._ai_analysis_job_wrapper,
            trigger=trigger,
            id=job_id,
            name="Daily AI Analysis",
            coalesce=True,
            max_instances=1,
        )

        self._job_ids.add(job_id)
        logger.info(
            "Registered AI analysis job: daily at %02d:00",
            self._config.ai_analysis_hour,
        )

    def _scrape_job_wrapper(self, data_type: str) -> None:
        """Execute a single scrape job.

        This is the actual function called by APScheduler. All exceptions
        are caught and logged so the scheduler continues running.
        """
        logger.info("Starting scrape job: %s", data_type)
        try:
            results = _safe_run_scrape_type(self._scraper, data_type)
            result = results.get(data_type)

            if result:
                if result.error:
                    logger.warning(
                        "Scrape job '%s' completed with error: %s",
                        data_type,
                        result.error,
                    )
                else:
                    logger.info(
                        "Scrape job '%s' completed: %d records",
                        data_type,
                        len(result.records),
                    )
            else:
                logger.info("Scrape job '%s' completed", data_type)

        except Exception as e:
            logger.error(
                "Unhandled exception in scrape job '%s': %s",
                data_type,
                e,
                exc_info=True,
            )

    def _ai_analysis_job_wrapper(self) -> None:
        """Execute the daily AI analysis job.

        [PLACEHOLDER] Currently logs that analysis would run here.
        Insert actual AI analysis logic below when implemented.
        """
        logger.info("Starting daily AI analysis job")
        try:
            logger.info("AI analysis would run here")

            # TODO: Insert actual AI analysis implementation here
            # Example flow:
            # 1. Query new records from database since last analysis
            # 2. Format records for AI prompt
            # 3. Call AI provider (Ollama/OpenAI/etc.)
            # 4. Persist analysis results/recommendations
            # 5. Send notifications if anomalies detected

            logger.info("AI analysis job completed")

        except Exception as e:
            logger.error("AI analysis job failed: %s", e, exc_info=True)
