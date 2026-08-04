"""Tests for the check golden path and DqReport."""

from collections.abc import Iterator
from datetime import UTC, datetime
from types import TracebackType
from typing import Any, Self

import pytest

from reade.core.enums import DbType
from reade.core.errors import DbError, DqError, RuleError, SqlError
from reade.data_io import execute_query
from reade.db import SqliteConnector
from reade.dq import (
    CompletenessDimension,
    DqResult,
    FreshnessDimension,
    VolumeDimension,
    check,
)


class DeadConnector:
    """A connector stub whose ``execute`` always fails with ``DbError``.

    Structurally satisfies ``ConnectionInterface`` so lower-layer
    propagation can be driven through check without a database.
    """

    db_type = DbType.SQLITE

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None

    def connect(self) -> None:
        return None

    def close(self) -> None:
        return None

    def is_connected(self) -> bool:
        return True

    def ping(self) -> bool:
        return True

    def execute(
        self, sql: str, params: dict[str, Any] | None = None
    ) -> list[tuple[Any, ...]]:
        raise DbError("statement failed")


@pytest.fixture
def connector() -> Iterator[SqliteConnector]:
    with SqliteConnector(database=":memory:") as conn:
        execute_query(conn, "CREATE TABLE events (event_name TEXT, created_at TEXT)")
        now = datetime.now(UTC).replace(tzinfo=None)
        execute_query(
            conn,
            "INSERT INTO events VALUES (:name, :created_at)",
            {"name": "signup", "created_at": now.isoformat(sep=" ")},
        )
        execute_query(conn, "CREATE TABLE empty_events (created_at TEXT)")
        yield conn


class TestCheck:
    def test_report_passes_when_every_dimension_measures_and_passes(
        self, connector: SqliteConnector
    ) -> None:
        report = check(
            connector,
            dims=[
                VolumeDimension(table="events", min_rows=1),
                FreshnessDimension(
                    table="events", column="created_at", max_delay_seconds=3600
                ),
                CompletenessDimension(table="events", columns=["event_name"]),
            ],
        )

        assert report.passed
        assert len(report.entries) == 3
        names = [
            entry.dimension for entry in report.entries if isinstance(entry, DqResult)
        ]
        assert names == ["volume", "freshness", "completeness"]

    def test_failed_dimension_fails_the_report_as_a_result(
        self, connector: SqliteConnector
    ) -> None:
        # Failed is a measured verdict: the entry is a DqResult with
        # passed=False — the other direction of overall passed.
        report = check(connector, dims=[VolumeDimension(table="events", min_rows=100)])

        assert not report.passed
        entry = report.entries[0]
        assert isinstance(entry, DqResult)
        assert not entry.passed

    def test_errored_dimension_reports_distinct_from_failed(
        self, connector: SqliteConnector
    ) -> None:
        # The split semantic's report half: freshness over an empty
        # table cannot measure — check catches the RuleError and the
        # entry IS the error, never a DqResult with passed=False. The
        # report keeps the other dimensions' verdicts instead of
        # aborting, and overall passed requires measured AND passed.
        report = check(
            connector,
            dims=[
                VolumeDimension(table="events", min_rows=1),
                FreshnessDimension(
                    table="empty_events",
                    column="created_at",
                    max_delay_seconds=3600,
                ),
            ],
        )

        assert not report.passed
        measured = report.entries[0]
        errored = report.entries[1]
        assert isinstance(measured, DqResult)
        assert measured.passed
        assert isinstance(errored, RuleError)
        assert not isinstance(errored, DqResult)

    def test_entries_follow_dims_order(self, connector: SqliteConnector) -> None:
        report = check(
            connector,
            dims=[
                CompletenessDimension(table="events", columns=["event_name"]),
                VolumeDimension(table="events", min_rows=1),
            ],
        )

        names = [
            entry.dimension for entry in report.entries if isinstance(entry, DqResult)
        ]
        assert names == ["completeness", "volume"]

    def test_sql_error_propagates_uncaught_through_check(
        self, connector: SqliteConnector
    ) -> None:
        # The catch scope is RuleError ONLY. A hostile identifier in a
        # dimension is a caller bug, not a data condition: SqlError
        # propagates uncaught — it is never an errored report entry.
        with pytest.raises(SqlError):
            check(
                connector,
                dims=[
                    FreshnessDimension(
                        table="events; DROP TABLE events",
                        column="created_at",
                        max_delay_seconds=3600,
                    )
                ],
            )

    def test_db_error_propagates_uncaught_through_check(self) -> None:
        # A dead connection aborts the report rather than becoming a
        # per-dimension verdict: DbError passes through unwrapped.
        with pytest.raises(DbError):
            check(
                DeadConnector(),
                dims=[VolumeDimension(table="events", min_rows=1)],
            )

    def test_empty_dims_is_a_caller_bug(self, connector: SqliteConnector) -> None:
        # A report over zero dimensions would pass vacuously — the
        # same misreporting class the completeness guards refuse,
        # mirrored at the report layer.
        with pytest.raises(DqError):
            check(connector, dims=[])
