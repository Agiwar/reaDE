"""Connection interface protocol for health checking."""

from types import TracebackType
from typing import Protocol, Self


class ConnectionInterface(Protocol):
    """Protocol for connection lifecycle and health checking.

    The contract for reaDE database connectors. Other connection-like
    resources with the same lifecycle (establish, health-check, close)
    can satisfy it structurally, but the SDK's error taxonomy and
    health-check semantics are designed around database connections.
    """

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
