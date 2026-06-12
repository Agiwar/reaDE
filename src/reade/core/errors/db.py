"""Database connection exceptions."""

from reade.core.errors.base import ReadeError


class DbError(ReadeError):
    """Raised when a database operation fails at the driver boundary.

    Covers the connection lifecycle (connect, health check, close) and
    statement execution. Connectors map driver-specific exceptions into
    this error.
    """


class NotConnectedError(DbError):
    """Raised when a connection is used before connect() establishes it.

    Accessing a connector's underlying driver connection, or executing
    work through it, requires an established connection.
    """
