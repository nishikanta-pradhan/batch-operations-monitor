"""Application-specific errors with user-facing messages."""


class MonitorError(Exception):
    """Base class for expected operational errors."""


class ValidationError(MonitorError):
    """Raised when supplied data violates a domain constraint."""


class ImportFileError(MonitorError):
    """Raised when an import file is missing or structurally invalid."""


class UnknownJobError(MonitorError):
    """Raised when an execution references an unregistered job."""

