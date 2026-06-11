"""SQL rendering exceptions."""

from reade.core.errors.base import ReadeError


class SqlError(ReadeError):
    """Raised when rendering a SQL template fails."""
