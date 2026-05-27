class PlmBaseError(Exception):
    """Base exception for all PLM-related errors."""

    def __init__(self, message: str | None = None, status_code: int = 500) -> None:
        self.message = message or "An unexpected PLM error occurred"
        self.status_code = status_code
        super().__init__(self.message)


class PlmAuthError(PlmBaseError):
    """Authentication failure with PLM system."""

    def __init__(self, message: str | None = None, status_code: int = 401) -> None:
        super().__init__(message or "PLM authentication failed", status_code)


class PlmConnectionError(PlmBaseError):
    """Network or connection failure with PLM system."""

    def __init__(self, message: str | None = None, status_code: int = 503) -> None:
        super().__init__(message or "Failed to connect to PLM system", status_code)


class PlmApiError(PlmBaseError):
    """PLM API returned an error response."""

    def __init__(self, message: str | None = None, status_code: int = 502) -> None:
        super().__init__(message or "PLM API returned an error", status_code)


class PlmDataError(PlmBaseError):
    """Error parsing or processing PLM data."""

    def __init__(self, message: str | None = None, status_code: int = 422) -> None:
        super().__init__(message or "Failed to process PLM data", status_code)


class ConfigError(Exception):
    """Configuration error."""

    def __init__(self, message: str | None = None) -> None:
        self.message = message or "Invalid configuration"
        super().__init__(self.message)
