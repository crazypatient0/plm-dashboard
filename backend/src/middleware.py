from __future__ import annotations

import json
import time
from typing import Any

from src.exceptions import PlmBaseError
from src.logger import get_logger

logger = get_logger("plm.middleware")


class RequestLoggingMiddleware:
    """ASGI middleware that logs each request with method, path, status, and duration."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start = time.monotonic()
        method = scope.get("method", "UNKNOWN")
        path = scope.get("path", "/")

        status_code = [0]

        async def log_send(message: dict[str, Any]) -> None:
            if message["type"] == "http.response.start":
                status_code[0] = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, log_send)
        except Exception:
            duration = time.monotonic() - start
            logger.exception(
                "Request failed",
                extra={"method": method, "path": path, "duration_ms": round(duration * 1000)},
            )
            raise
        else:
            duration = time.monotonic() - start
            logger.info(
                "Request completed",
                extra={
                    "method": method,
                    "path": path,
                    "status": status_code[0],
                    "duration_ms": round(duration * 1000),
                },
            )


class ExceptionHandlingMiddleware:
    """ASGI middleware that catches PlmBaseError and returns a proper JSON error response."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        try:
            await self.app(scope, receive, send)
        except PlmBaseError as exc:
            body = json.dumps({"error": exc.message, "status_code": exc.status_code}).encode()
            headers = [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
            ]

            await send({
                "type": "http.response.start",
                "status": exc.status_code,
                "headers": headers,
            })
            await send({
                "type": "http.response.body",
                "body": body,
            })
