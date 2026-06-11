"""Database connection exceptions."""

from reade.core.errors.base import ReadeError


class DbError(ReadeError):
    """Raised when a database connection operation fails.

    Covers the connection lifecycle: connect, health check, and close.
    Connectors map driver-specific exceptions into this error.
    """


class NotConnectedError(DbError):
    """Raised when a connection is used before connect() establishes it.

    Accessing a connector's underlying driver connection, or executing
    work through it, requires an established connection.
    """
