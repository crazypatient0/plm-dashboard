"""FastAPI application factory — creates configured app instances.

Separated from ``main.py`` so tests can import the factory without
triggering module-level side effects.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.api.routes import router
from src.config import Settings, get_settings
from src.logger import get_logger, setup_logging
from src.middleware import ExceptionHandlingMiddleware, RequestLoggingMiddleware
from src.models import Base
from src.scheduler import SchedulerService, ScrapeIntervalConfig, create_scraper_from_settings

logger = get_logger(__name__)


CORS_ORIGINS: list[str] = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:3000",
    "http://localhost:8080",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:3000",
]


def _get_sync_database_url(url: str) -> str:
    """Convert an async database URL to its sync equivalent."""
    return url.replace("sqlite+aiosqlite://", "sqlite://")


def configure_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure a FastAPI application instance.

    Args:
        settings: Optional Settings override (used in tests).  Falls back
            to ``get_settings()`` when ``None``.

    Returns:
        Fully configured FastAPI app ready for ``uvicorn`` or ``TestClient``.
    """

    resolved = settings or get_settings()

    # ------------------------------------------------------------------
    # Lifespan
    # ------------------------------------------------------------------

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        """Application startup/shutdown lifecycle."""
        setup_logging(resolved.LOG_LEVEL)

        sync_url = _get_sync_database_url(resolved.DATABASE_URL)
        engine = create_engine(sync_url, echo=False, pool_pre_ping=True)
        session_factory = sessionmaker(bind=engine)

        Base.metadata.create_all(engine)

        app.state.db_engine = engine
        app.state.db_session_factory = session_factory
        app.state.scheduler = None
        app.state.scraper = None

        try:
            scraper = create_scraper_from_settings(resolved)
            app.state.scraper = scraper

            config = ScrapeIntervalConfig.from_settings(resolved)
            scheduler = SchedulerService(scraper=scraper, config=config)
            scheduler.start()
            app.state.scheduler = scheduler

            logger.info("Application started — scheduler=%s", scheduler.is_running)
        except Exception:
            logger.exception(
                "Startup incomplete — scheduler/scraper not available. "
                "Some endpoints will return 503.",
            )

        yield  # -- app runs here --

        # -- shutdown --
        if hasattr(app.state, "scheduler") and app.state.scheduler is not None:
            try:
                app.state.scheduler.stop()
            except Exception:
                logger.exception("Error stopping scheduler")

        if hasattr(app.state, "db_engine"):
            try:
                app.state.db_engine.dispose()
            except Exception:
                logger.exception("Error disposing database engine")

        logger.info("Application shut down")

    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------

    app = FastAPI(
        title="PLM Dashboard API",
        version="0.1.0",
        description="Backend API for PLM data monitoring and analysis dashboard",
        lifespan=lifespan,
    )

    # -- Middleware stack (innermost first) --
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(ExceptionHandlingMiddleware)
    app.add_middleware(RequestLoggingMiddleware)

    app.include_router(router)

    return app
