"""Private connect-retry loop shared by the server-backed connectors."""

import time
from collections.abc import Callable


def connect_with_retry[T](
    open_connection: Callable[[], T],
    *,
    attempts: int,
    backoff: float,
    retry_on: tuple[type[Exception], ...],
) -> T:
    """Call ``open_connection`` up to ``attempts`` times.

    The delay before the second attempt is ``backoff`` seconds and
    doubles after each subsequent failure. Only connection establishment
    is ever retried — statement execution and health checks are not:
    retrying execution repeats non-idempotent work, and a health check
    that retries internally hides flapping from the caller. The final
    failure is re-raised unchanged; mapping driver exceptions into
    ``DbError`` stays in the connector.

    Args:
        open_connection: Zero-argument callable that establishes and
            returns the driver connection.
        attempts: Total number of attempts; must be at least 1.
        backoff: Delay before the second attempt, in seconds.
        retry_on: Driver exception types that trigger a retry; anything
            else propagates immediately.

    Returns:
        The value returned by ``open_connection``.

    Raises:
        ValueError: If ``attempts`` is less than 1.
        Exception: The last ``retry_on`` exception, unchanged, once all
            attempts are exhausted.
    """
    if attempts < 1:
        raise ValueError(f"attempts must be >= 1, got {attempts}")
    delay = backoff
    for attempt in range(1, attempts + 1):
        try:
            return open_connection()
        except retry_on:
            if attempt == attempts:
                raise
            time.sleep(delay)
            delay *= 2
    raise AssertionError("unreachable")  # pragma: no cover
