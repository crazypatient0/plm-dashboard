"""FastAPI route definitions for the PLM Dashboard API.

Organized into prefix groups:
  /api/health        — Health check
  /api/records       — Data access (CRUD, search, summary, prune)
  /api/logs          — Scrape log retrieval
  /api/scrape        — On-demand scrape execution
  /api/scheduler     — Background scheduler management
  /api/notifications — Test notification sending
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.config import Settings, get_settings
from src.logger import get_logger
from src.notifications.dingtalk import send_dingtalk_message
from src.notifications.teams import send_teams_message
from src.scheduler import SchedulerService
from src.scraper import Scraper
from src.storage import DataAccessLayer

logger = get_logger(__name__)

router = APIRouter(prefix="/api")

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: datetime


class ScrapeRunRequest(BaseModel):
    data_type: str | None = None  # None = scrape all


class ScrapeRunResponse(BaseModel):
    status: str
    message: str
    results: dict | None = None


class SchedulerStatusResponse(BaseModel):
    running: bool


class NotificationTestRequest(BaseModel):
    channel: str  # "teams" | "dingtalk"
    title: str = "PLM Dashboard - Test Notification"
    message: str = "This is a test notification from PLM Dashboard."


class NotificationTestResponse(BaseModel):
    success: bool
    message: str


class PruneResponse(BaseModel):
    records_deleted: int
    logs_deleted: int


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------


def get_db(request: Request) -> Session:
    """Yield a SQLAlchemy session from the app's session factory."""
    factory = request.app.state.db_session_factory
    db: Session = factory()
    try:
        yield db
    finally:
        db.close()


def get_dal(db: Session = Depends(get_db)) -> DataAccessLayer:
    """Provide a DataAccessLayer wired to the current session."""
    return DataAccessLayer(session=db)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health() -> HealthResponse:
    """Basic health check endpoint."""
    return HealthResponse(
        status="ok",
        version="0.1.0",
        timestamp=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------


@router.get("/records/{data_type}", tags=["Records"])
def get_current_records(
    data_type: str,
    limit: int = Query(default=100, ge=1, le=1000),
    dal: DataAccessLayer = Depends(get_dal),
) -> list[dict]:
    """Return the latest N records for a given data type from the current snapshot."""
    records = dal.get_current_records(data_type, limit=limit)
    return [_serialize_current_record(r) for r in records]


@router.get("/records/{data_type}/history", tags=["Records"])
def get_history_records(
    data_type: str,
    limit: int = Query(default=100, ge=1, le=1000),
    dal: DataAccessLayer = Depends(get_dal),
) -> list[dict]:
    """Return the full history of records for a given data type."""
    records = dal.get_latest_records(data_type, limit=limit)
    return [_serialize_history_record(r) for r in records]


@router.get("/records/{data_type}/range", tags=["Records"])
def get_records_by_range(
    data_type: str,
    since: str = Query(description="ISO 8601 datetime"),
    until: str | None = Query(default=None, description="ISO 8601 datetime"),
    dal: DataAccessLayer = Depends(get_dal),
) -> list[dict]:
    """Return records within a time range for a given data type."""
    try:
        since_dt = datetime.fromisoformat(since)
        until_dt = datetime.fromisoformat(until) if until else None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid datetime: {e}") from e

    records = dal.get_records_by_time_range(data_type, since=since_dt, until=until_dt)
    return [_serialize_record(r) for r in records]


@router.get("/records/{data_type}/count", tags=["Records"])
def get_records_count(
    data_type: str,
    dal: DataAccessLayer = Depends(get_dal),
) -> dict:
    """Return the record count for a given data type (history total and current snapshot)."""
    history_count = dal.get_records_count(data_type)
    current_count = dal.get_current_count(data_type)
    return {
        "data_type": data_type,
        "history_count": history_count,
        "current_count": current_count,
    }


@router.get("/records/{data_type}/summary", tags=["Records"])
def get_records_summary(
    data_type: str,
    dal: DataAccessLayer = Depends(get_dal),
) -> dict:
    """Return summary statistics for a given data type."""
    summary = dal.get_summary(data_type)
    return {
        "total": summary["total"],
        "latest_scraped_at": _format_bj_time(summary["latest_scraped_at"]),
        "oldest_scraped_at": _format_bj_time(summary["oldest_scraped_at"]),
    }


@router.get("/records/{data_type}/search", tags=["Records"])
def search_records(
    data_type: str,
    field: str = Query(description="Field name to search in raw_data"),
    value: str = Query(description="Search value (case-insensitive)"),
    dal: DataAccessLayer = Depends(get_dal),
) -> list[dict]:
    """Search records by a field value in the raw_data JSON."""
    records = dal.search_records(data_type, field=field, value=value)
    return [_serialize_record(r) for r in records]


@router.delete("/records/prune", response_model=PruneResponse, tags=["Records"])
def prune_old_data(
    retention_days: int = Query(default=90, ge=0, le=730),
    data_type: str | None = Query(default=None),
    dal: DataAccessLayer = Depends(get_dal),
) -> PruneResponse:
    """Delete records and logs older than retention_days. Use retention_days=0 to delete ALL history."""
    if retention_days == 0:
        records_deleted = dal.delete_all_history(data_type=data_type)
        logs_deleted = dal.prune_old_logs(retention_days=0)
    else:
        records_deleted = dal.prune_old_data(retention_days=retention_days)
        logs_deleted = dal.prune_old_logs(retention_days=retention_days)
    return PruneResponse(records_deleted=records_deleted, logs_deleted=logs_deleted)


# ---------------------------------------------------------------------------
# Logs
# ---------------------------------------------------------------------------


@router.get("/logs", tags=["Logs"])
def get_logs(
    data_type: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=200),
    dal: DataAccessLayer = Depends(get_dal),
) -> list[dict]:
    """Return recent scrape logs, optionally filtered by data_type."""
    logs = dal.get_recent_logs(data_type=data_type, limit=limit)
    return [_serialize_log(l) for l in logs]


# ---------------------------------------------------------------------------
# Scraper
# ---------------------------------------------------------------------------


def _get_scraper(request: Request) -> Scraper | None:
    """Return the app's scraper instance, or None if not initialized."""
    return getattr(request.app.state, "scraper", None)


@router.post("/scrape/run", response_model=ScrapeRunResponse, tags=["Scraper"])
def run_scrape(
    body: ScrapeRunRequest,
    request: Request,
) -> ScrapeRunResponse:
    """Trigger an on-demand scrape for all types or a specific type."""
    scraper = _get_scraper(request)
    if scraper is None:
        raise HTTPException(status_code=503, detail="Scraper not initialized")

    try:
        if body.data_type and body.data_type not in ("part", "document", "conversion"):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid data_type: {body.data_type}. "
                f"Expected one of: part, document, conversion, or null for all.",
            )

        if body.data_type:
            # Import here to avoid circular dependency at module level
            from src.scheduler import _safe_run_scrape_type

            results = _safe_run_scrape_type(scraper, body.data_type)
        else:
            results = scraper.scrape_all()

        return ScrapeRunResponse(
            status="success",
            message=f"Scrape completed for {body.data_type or 'all types'}",
            results={
                k: {"records": len(v.records), "error": v.error}
                for k, v in results.items()
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Scrape failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/scrape/status", tags=["Scraper"])
def scrape_status(request: Request) -> dict:
    """Return whether the scraper is initialized."""
    scraper = _get_scraper(request)
    return {"initialized": scraper is not None}


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------


def _get_scheduler(request: Request) -> SchedulerService | None:
    """Return the app's scheduler instance, or None if not initialized."""
    return getattr(request.app.state, "scheduler", None)


@router.get("/scheduler/status", response_model=SchedulerStatusResponse, tags=["Scheduler"])
def scheduler_status(request: Request) -> SchedulerStatusResponse:
    """Return whether the scheduler is running."""
    scheduler = _get_scheduler(request)
    return SchedulerStatusResponse(running=scheduler is not None and scheduler.is_running)


@router.get("/scheduler/jobs", tags=["Scheduler"])
def scheduler_jobs(request: Request) -> list[dict]:
    """Return metadata about registered scheduler jobs."""
    scheduler = _get_scheduler(request)
    if scheduler is None:
        raise HTTPException(status_code=503, detail="Scheduler not initialized")
    return scheduler.get_jobs()


@router.post("/scheduler/start", response_model=SchedulerStatusResponse, tags=["Scheduler"])
def scheduler_start(request: Request) -> SchedulerStatusResponse:
    """Start the background scheduler."""
    scheduler = _get_scheduler(request)
    if scheduler is None:
        raise HTTPException(status_code=503, detail="Scheduler not initialized")
    scheduler.start()
    return SchedulerStatusResponse(running=True)


@router.post("/scheduler/stop", response_model=SchedulerStatusResponse, tags=["Scheduler"])
def scheduler_stop(request: Request) -> SchedulerStatusResponse:
    """Stop the background scheduler."""
    scheduler = _get_scheduler(request)
    if scheduler is None:
        raise HTTPException(status_code=503, detail="Scheduler not initialized")
    scheduler.stop()
    return SchedulerStatusResponse(running=False)


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------


@router.post("/notifications/test", response_model=NotificationTestResponse, tags=["Notifications"])
def send_test_notification(
    body: NotificationTestRequest,
    settings: Settings = Depends(get_settings),
) -> NotificationTestResponse:
    """Send a test notification to Teams or DingTalk."""


    if body.channel == "teams":
        webhook = settings.TEAMS_WEBHOOK_URL
        if not webhook:
            raise HTTPException(status_code=400, detail="Teams webhook URL not configured")
        success = send_teams_message(webhook_url=webhook, title=body.title, message=body.message)
    elif body.channel == "dingtalk":
        webhook = settings.DINGTALK_WEBHOOK_URL
        if not webhook:
            raise HTTPException(status_code=400, detail="DingTalk webhook URL not configured")
        success = send_dingtalk_message(webhook_url=webhook, title=body.title, message=body.message)
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported channel: {body.channel}. Use 'teams' or 'dingtalk'.",
        )

    return NotificationTestResponse(
        success=success,
        message="Notification sent" if success else "Notification failed",
    )


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------


def _serialize_record(record) -> dict:
    """Convert a ScrapeRecord ORM object to a JSON-safe dict."""
    return {
        "id": record.id,
        "data_type": record.data_type,
        "raw_data": record.raw_data,
        "scraped_at": record.scraped_at.isoformat() if record.scraped_at else None,
        "created_at": record.created_at.isoformat() if hasattr(record, "created_at") and record.created_at else None,
    }


def _format_bj_time(dt) -> str | None:
    """Format a datetime as ISO string with explicit +08:00 timezone suffix.

    SQLite stores naive datetimes. Since we store all times as Beijing time,
    we append +08:00 so JavaScript parses it correctly regardless of browser tz.
    """
    if dt is None:
        return None
    iso = dt.isoformat()
    # Already has tz info (e.g. +08:00 or Z)
    if dt.tzinfo is not None:
        return iso
    # Naive datetime — append +08:00 to make timezone unambiguous
    return f"{iso}+08:00"


def _serialize_current_record(record) -> dict:
    """Convert a ScrapeCurrent ORM object to a JSON-safe dict."""
    return {
        "id": record.id,
        "data_type": record.data_type,
        "item_key": record.item_key,
        "item_index": record.item_index,
        "raw_data": record.raw_data,
        "scraped_at": _format_bj_time(record.scraped_at),
        "created_at": _format_bj_time(record.created_at) if hasattr(record, "created_at") and record.created_at else None,
    }


def _serialize_history_record(record) -> dict:
    """Convert a ScrapeHistory ORM object to a JSON-safe dict."""
    return {
        "id": record.id,
        "data_type": record.data_type,
        "raw_data": record.raw_data,
        "scraped_at": _format_bj_time(record.scraped_at),
        "created_at": _format_bj_time(record.created_at) if hasattr(record, "created_at") and record.created_at else None,
    }


def _serialize_log(log) -> dict:
    """Convert a ScrapeLog ORM object to a JSON-safe dict."""
    return {
        "id": log.id,
        "data_type": log.data_type,
        "status": log.status,
        "records_count": log.records_count,
        "error_message": log.error_message,
        "started_at": _format_bj_time(log.started_at),
        "completed_at": _format_bj_time(log.completed_at),
    }
