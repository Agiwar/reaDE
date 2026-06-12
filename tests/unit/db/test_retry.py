"""Unit tests for the private connect-retry loop."""

import time
from typing import TYPE_CHECKING

import pytest

from reade.db._retry import connect_with_retry

if TYPE_CHECKING:
    from collections.abc import Iterator


class FlakyError(Exception):
    pass


class OtherError(Exception):
    pass


@pytest.fixture
def sleeps(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    recorded: list[float] = []
    monkeypatch.setattr(time, "sleep", recorded.append)
    return recorded


class TestConnectWithRetry:
    def test_first_success_returns_without_sleeping(self, sleeps: list[float]) -> None:
        result = connect_with_retry(
            lambda: "connection", attempts=3, backoff=0.5, retry_on=(FlakyError,)
        )

        assert result == "connection"
        assert sleeps == []

    def test_retries_with_doubling_backoff_then_succeeds(
        self, sleeps: list[float]
    ) -> None:
        outcomes: Iterator[FlakyError | str] = iter(
            [FlakyError("blip"), FlakyError("blip"), "connection"]
        )

        def flaky() -> str:
            outcome = next(outcomes)
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

        result = connect_with_retry(
            flaky, attempts=3, backoff=0.5, retry_on=(FlakyError,)
        )

        assert result == "connection"
        assert sleeps == [0.5, 1.0]

    def test_exhausted_attempts_reraise_last_error_unchanged(
        self, sleeps: list[float]
    ) -> None:
        def always_failing() -> str:
            raise FlakyError("down")

        with pytest.raises(FlakyError, match="down"):
            connect_with_retry(
                always_failing, attempts=3, backoff=0.5, retry_on=(FlakyError,)
            )

        assert sleeps == [0.5, 1.0]

    def test_unlisted_exception_propagates_immediately(
        self, sleeps: list[float]
    ) -> None:
        def wrong_failure() -> str:
            raise OtherError("not transient")

        with pytest.raises(OtherError):
            connect_with_retry(
                wrong_failure, attempts=3, backoff=0.5, retry_on=(FlakyError,)
            )

        assert sleeps == []

    def test_single_attempt_never_sleeps(self, sleeps: list[float]) -> None:
        def failing() -> str:
            raise FlakyError("down")

        with pytest.raises(FlakyError):
            connect_with_retry(failing, attempts=1, backoff=0.5, retry_on=(FlakyError,))

        assert sleeps == []

    def test_backoff_caps_at_max_delay(self, sleeps: list[float]) -> None:
        # Deploy-tunable attempt counts must not compound into unbounded
        # sleeps: doubling stops at the 30s ceiling.
        def always_failing() -> str:
            raise FlakyError("down")

        with pytest.raises(FlakyError):
            connect_with_retry(
                always_failing, attempts=4, backoff=20.0, retry_on=(FlakyError,)
            )

        assert sleeps == [20.0, 30.0, 30.0]

    def test_attempts_below_one_raise_value_error(self) -> None:
        with pytest.raises(ValueError, match="attempts"):
            connect_with_retry(
                lambda: "connection", attempts=0, backoff=0.5, retry_on=(FlakyError,)
            )
