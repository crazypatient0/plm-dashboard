"""Tests for the PLM exception hierarchy."""

from __future__ import annotations

from src.exceptions import (
    ConfigError,
    PlmApiError,
    PlmAuthError,
    PlmBaseError,
    PlmConnectionError,
    PlmDataError,
)


class TestPlmBaseError:
    def test_default_message(self) -> None:
        exc = PlmBaseError()
        assert exc.message == "An unexpected PLM error occurred"
        assert exc.status_code == 500

    def test_custom_message(self) -> None:
        exc = PlmBaseError("custom error", status_code=400)
        assert exc.message == "custom error"
        assert exc.status_code == 400

    def test_str_representation(self) -> None:
        exc = PlmBaseError("test message")
        assert str(exc) == "test message"


class TestPlmAuthError:
    def test_default(self) -> None:
        exc = PlmAuthError()
        assert exc.message == "PLM authentication failed"
        assert exc.status_code == 401
        assert isinstance(exc, PlmBaseError)

    def test_custom_message(self) -> None:
        exc = PlmAuthError("Session expired", status_code=403)
        assert exc.message == "Session expired"
        assert exc.status_code == 403


class TestPlmConnectionError:
    def test_default(self) -> None:
        exc = PlmConnectionError()
        assert exc.message == "Failed to connect to PLM system"
        assert exc.status_code == 503
        assert isinstance(exc, PlmBaseError)


class TestPlmApiError:
    def test_default(self) -> None:
        exc = PlmApiError()
        assert exc.message == "PLM API returned an error"
        assert exc.status_code == 502
        assert isinstance(exc, PlmBaseError)


class TestPlmDataError:
    def test_default(self) -> None:
        exc = PlmDataError()
        assert exc.message == "Failed to process PLM data"
        assert exc.status_code == 422
        assert isinstance(exc, PlmBaseError)


class TestConfigError:
    def test_default(self) -> None:
        exc = ConfigError()
        assert exc.message == "Invalid configuration"

    def test_custom(self) -> None:
        exc = ConfigError("Missing API key")
        assert exc.message == "Missing API key"
        assert str(exc) == "Missing API key"

    def test_not_plm_base(self) -> None:
        """ConfigError inherits from Exception, not PlmBaseError."""
        assert not issubclass(ConfigError, PlmBaseError)
        assert issubclass(ConfigError, Exception)
