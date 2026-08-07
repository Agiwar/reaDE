"""Connection interface protocol for health checking and execution."""

from types import TracebackType
from typing import Any, Protocol, Self

from reade.core.enums.db_type import DbType


class ConnectionInterface(Protocol):
    """Protocol for connection lifecycle, health checking, and execution.

    The contract for reaDE database connectors. Other connection-like
    resources with the same lifecycle (establish, health-check, close)
    can satisfy it structurally, but the SDK's error taxonomy and
    health-check semantics are designed around database connections.

    Stability: stable.
    """

    @property
    def db_type(self) -> DbType:
        """The database dialect the connection speaks.

        Read-only: consumers key dialect-specific behavior off it —
        e.g. SQL rendering via ``render_template(name,
        connector.db_type, context)`` — so the dialect can never
        disagree with the connection it describes. Implementations may
        declare it as a class-level constant or a per-instance value.

        Returns:
            The dialect of the underlying connection.
        """
        ...

    def __enter__(self) -> Self:
        """Enter the runtime context, establishing the connection.

        Entering the context is equivalent to calling connect().

        Returns:
            The connection interface instance.
        """
        ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Exit the runtime context, closing the connection.

        Equivalent to calling close(), including its no-op guarantee.

        Args:
            exc_type: The exception type.
            exc_value: The exception value.
            traceback: The traceback object.
        """
        ...

    def connect(self) -> None:
        """Establish the connection."""
        ...

    def close(self) -> None:
        """Close the connection.

        Closing an unconnected or already-closed connection is a no-op.
        """
        ...

    def is_connected(self) -> bool:
        """Check if the connection is active.

        Only consults local state; it cannot detect server-side timeouts
        or half-open connections. Use ping() for an end-to-end check.

        Returns:
            True if connected, False otherwise.
        """
        ...

    def ping(self) -> bool:
        """Perform an active, round-trip health check on the connection.

        Unlike is_connected(), which may only check local state, ping()
        must verify the peer end-to-end (e.g., ``SELECT 1`` for databases).

        Returns:
            True if the connection is healthy, False otherwise.
        """
        ...

    def execute(
        self, sql: str, params: dict[str, Any] | None = None, /
    ) -> list[tuple[Any, ...]]:
        """Execute a SQL statement and return all result rows, materialized.

        Statements without a result set (DDL, INSERT) return an empty
        list. Driver specifics — cursors, fetch styles — are the
        implementation's concern and never leak to callers.

        Falsy ``params`` (``None`` or an empty mapping) MUST be
        normalized to no-parameters before reaching the driver; this is
        part of the interface contract for every implementation, not a
        convenience of the shipped connectors. Rationale: pyformat
        drivers %-format the statement whenever parameters are present,
        which would corrupt a literal ``%`` in a statement that binds
        nothing — so ``execute(rendered.sql, rendered.params)`` must be
        safe even when ``params`` is empty.

        Args:
            sql: The SQL statement to execute, in the dialect's
                placeholder style for any bound parameters.
            params: Values for the statement's placeholders, keyed by
                placeholder name (e.g. ``RenderedQuery.params``).
                ``None`` or ``{}`` mean the statement binds nothing.

        Returns:
            All result rows as tuples.

        Raises:
            NotConnectedError: If no connection is established.
            DbError: If the driver fails to execute the statement or
                fetch its results. The driver exception is attached as
                the cause.
        """
        ...
