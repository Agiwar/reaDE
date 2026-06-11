"""Data I/O exceptions."""

from reade.core.errors.base import ReadeError


class DataIoError(ReadeError):
    """Raised when executing a query or reading/writing results fails."""
