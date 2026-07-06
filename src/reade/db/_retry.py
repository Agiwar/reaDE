"""Private connect-retry loop shared by the server-backed connectors."""

import time
from collections.abc import Callable

_MAX_DELAY = 30.0


def connect_with_retry[T](
    open_connection: Callable[[], T],
    *,
    attempts: int,
    backoff: float,
    retry_on: tuple[type[Exception], ...],
) -> T:
    """Call ``open_connection`` up to ``attempts`` times.

    The delay before the second attempt is ``backoff`` seconds, doubling
    after each subsequent failure, capped at 30 seconds so deploy-tuned
    attempt counts cannot compound into unbounded sleeps. Only connection
    establishment is ever retried — statement execution and health checks
    are not: retrying execution repeats non-idempotent work, and a health
    check that retries internally hides flapping from the caller. The
    final failure is re-raised unchanged; mapping driver exceptions into
    ``DbError`` stays in the connector.

    ``retry_on`` deliberately spans each driver's full error family,
    permanent failures included — a bad password burns the configured
    attempts before surfacing. Classifying transient vs. permanent per
    driver is a taxonomy this helper does not attempt; bounded attempts
    and the delay cap keep the worst case priced. Jitter is deliberately
    absent: the golden path is a single batch job, not a fleet — herd
    behavior is a pooling-era concern.

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
            delay = min(delay * 2, _MAX_DELAY)
    raise AssertionError("unreachable")  # pragma: no cover
