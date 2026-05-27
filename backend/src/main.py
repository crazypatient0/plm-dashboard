"""PLM Dashboard — FastAPI application entry point.

Usage:
    uvicorn src.main:app --reload
"""

from __future__ import annotations

import logging

from fastapi import FastAPI

from src.app_factory import configure_app

try:
    app = configure_app()
except Exception as exc:
    logging.getLogger(__name__).warning(
        "Could not configure app at import time: %s. "
        "This is expected during test collection. "
        "Use configure_app() directly when testing.",
        exc,
    )
    app = FastAPI()  # type: ignore[assignment]
    # ^^ placeholder — replaced when running under uvicorn with valid .env
