"""Tests for the structured logging module."""

from __future__ import annotations

import json
import logging

from src import logger as logger_module
from src.logger import JsonFormatter, get_logger, setup_logging


class TestSetupLogging:
    def _reset_guard(self) -> None:
        """Reset the _LOG_CONFIGURED guard so setup_logging re-executes."""
        logger_module._LOG_CONFIGURED = False

    def test_setup_sets_level(self) -> None:
        self._reset_guard()
        root = logging.getLogger()
        root.setLevel(logging.WARNING)
        setup_logging("DEBUG")
        assert root.level == logging.DEBUG

    def test_setup_default_level(self) -> None:
        self._reset_guard()
        root = logging.getLogger()
        root.setLevel(logging.WARNING)
        setup_logging()
        assert root.level == logging.INFO

    def test_setup_idempotent(self) -> None:
        self._reset_guard()
        root = logging.getLogger()
        handler_count_before = len(root.handlers)
        setup_logging()
        handler_count = len(root.handlers)
        setup_logging()
        assert len(root.handlers) == handler_count
        # Clean up added handler so other tests aren't affected
        while len(root.handlers) > handler_count_before:
            root.handlers.pop()


class TestGetLogger:
    def test_returns_logger_with_name(self) -> None:
        logger = get_logger("test.logger")
        assert logger.name == "test.logger"
        assert isinstance(logger, logging.Logger)

    def test_returns_same_instance(self) -> None:
        a = get_logger("test.singleton")
        b = get_logger("test.singleton")
        assert a is b


class TestJsonFormatter:
    def test_formats_basic_record(self) -> None:
        logger = logging.getLogger("json.test")
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        # Capture the output as string
        import io

        stream = io.StringIO()
        handler.setStream(stream)

        logger.info("hello world")
        stream.seek(0)
        record_str = stream.read()

        parsed = json.loads(record_str.strip())
        assert parsed["level"] == "INFO"
        assert parsed["name"] == "json.test"
        assert parsed["message"] == "hello world"
        assert "timestamp" in parsed

    def test_formats_exception(self) -> None:
        logger = logging.getLogger("json.exc")
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        import io

        stream = io.StringIO()
        handler.setStream(stream)

        try:
            raise ValueError("test error")
        except ValueError:
            logger.exception("something went wrong")

        stream.seek(0)
        record_str = stream.read()
        parsed = json.loads(record_str.strip())

        assert parsed["level"] == "ERROR"
        assert "exception" in parsed
        assert "ValueError" in parsed["exception"]
        assert "test error" in parsed["exception"]
