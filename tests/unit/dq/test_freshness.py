"""Tests for FreshnessDimension."""

from collections.abc import Iterator
from datetime import UTC, datetime
from types import TracebackType
from typing import Any, Self

import pytest

from reade.core.enums import DbType
from reade.core.errors import DbError, RuleError, SqlError
from reade.data_io import execute_query
from reade.db import SqliteConnector
from reade.dq import FreshnessDimension


class DeadConnector:
    """A connector stub whose ``execute`` always fails with ``DbError``.

    Structurally satisfies ``ConnectionInterface`` so lower-layer
    propagation can be driven through a dimension without a database.
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
        execute_query(conn, "CREATE TABLE events (created_at TEXT)")
        yield conn


class TestFreshnessDimension:
    def test_empty_table_propagates_rule_error_not_a_verdict(
        self, connector: SqliteConnector
    ) -> None:
        # The split semantic's live case: DelayRule over an actual
        # empty table raises RuleError — unanswerable is not stale —
        # and the dimension propagates it rather than converting it
        # into a verdict. Reporting it as errored, distinct from
        # failed, is check's job, not the dimension's.
        dimension = FreshnessDimension(
            table="events", column="created_at", max_delay_seconds=3600
        )

        with pytest.raises(RuleError):
            dimension.assess(connector)

    def test_aggregates_passing_rule(self, connector: SqliteConnector) -> None:
        now = datetime.now(UTC).replace(tzinfo=None)
        execute_query(
            connector,
            "INSERT INTO events VALUES (:created_at)",
            {"created_at": now.isoformat(sep=" ")},
        )

        result = FreshnessDimension(
            table="events", column="created_at", max_delay_seconds=3600
        ).assess(connector)

        assert result.dimension == "freshness"
        assert result.passed
        assert len(result.rule_results) == 1
        assert result.rule_results[0].rule == "delay"

    def test_fails_as_result_when_rule_fails(self, connector: SqliteConnector) -> None:
        execute_query(
            connector,
            "INSERT INTO events VALUES ('2020-01-01 00:00:00')",
        )

        result = FreshnessDimension(
            table="events", column="created_at", max_delay_seconds=60
        ).assess(connector)

        assert not result.passed
        assert not result.rule_results[0].passed

    def test_all_null_column_propagates_rule_error(
        self, connector: SqliteConnector
    ) -> None:
        # MAX over an all-NULL column yields nothing — the same
        # unanswerable class as the empty table, per the aggregate-NULL
        # principle.
        execute_query(connector, "INSERT INTO events VALUES (NULL)")

        dimension = FreshnessDimension(
            table="events", column="created_at", max_delay_seconds=3600
        )

        with pytest.raises(RuleError):
            dimension.assess(connector)

    def test_hostile_identifier_raises_sql_error_through_the_dimension(
        self, connector: SqliteConnector
    ) -> None:
        # A hostile identifier in a dimension is a caller bug, not a
        # data condition: SqlError raises at render, propagates through
        # assess, and never reaches the database.
        dimension = FreshnessDimension(
            table="events; DROP TABLE events",
            column="created_at",
            max_delay_seconds=3600,
        )

        with pytest.raises(SqlError):
            dimension.assess(connector)

    def test_lower_layer_errors_propagate_unchanged(self) -> None:
        # The Dimension protocol's propagate clause: ReadeErrors from
        # lower layers pass through assess unwrapped.
        dimension = FreshnessDimension(
            table="events", column="created_at", max_delay_seconds=3600
        )

        with pytest.raises(DbError):
            dimension.assess(DeadConnector())
