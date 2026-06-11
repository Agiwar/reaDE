"""Data quality exceptions."""

from reade.core.errors.base import ReadeError


class DqError(ReadeError):
    """Raised when computing a data quality dimension fails."""
