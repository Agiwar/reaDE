"""Tests for NullCountRule."""

from collections.abc import Iterator
from types import TracebackType
from typing import Any, Self

import pytest

from reade.core.enums import DbType
from reade.core.errors import DbError, RuleError, SqlError
from reade.data_io import execute_query
from reade.db import SqliteConnector
from reade.sql import render_template
from reade.validation import NullCountRule

HOSTILE_IDENTIFIERS = ["events; DROP TABLE events", 'events"--']


class NoRowsConnector:
    """A connector stub whose ``execute`` returns no rows at all."""

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
        return []


@pytest.fixture
def connector() -> Iterator[SqliteConnector]:
    with SqliteConnector(database=":memory:") as conn:
        execute_query(conn, "CREATE TABLE events (event_name TEXT, created_at TEXT)")
        yield conn


def _insert(conn: SqliteConnector, name: str | None, created_at: str | None) -> None:
    execute_query(
        conn,
        "INSERT INTO events VALUES (:name, :created_at)",
        {"name": name, "created_at": created_at},
    )


class TestNullCountRule:
    def test_passes_when_nulls_at_threshold(self, connector: SqliteConnector) -> None:
        _insert(connector, "signup", "2026-08-01")
        _insert(connector, None, "2026-08-02")

        result = NullCountRule(
            table="events", column="event_name", max_nulls=1
        ).evaluate(connector)

        assert result.passed
        assert result.rule == "null_count"
        assert result.observed == 1
        assert result.threshold == 1

    def test_fails_as_result_not_exception_when_above_threshold(
        self, connector: SqliteConnector
    ) -> None:
        _insert(connector, None, "2026-08-01")
        _insert(connector, None, "2026-08-02")

        result = NullCountRule(
            table="events", column="event_name", max_nulls=1
        ).evaluate(connector)

        assert not result.passed
        assert result.observed == 2
        assert result.threshold == 1

    def test_default_threshold_is_zero_nulls(self, connector: SqliteConnector) -> None:
        _insert(connector, "signup", "2026-08-01")

        clean = NullCountRule(table="events", column="event_name").evaluate(connector)
        assert clean.passed
        assert clean.observed == 0

        _insert(connector, None, "2026-08-02")
        dirty = NullCountRule(table="events", column="event_name").evaluate(connector)
        assert not dirty.passed
        assert dirty.observed == 1

    def test_counts_only_the_named_column(self, connector: SqliteConnector) -> None:
        # A NULL in another column is that column's problem.
        _insert(connector, "signup", None)

        result = NullCountRule(table="events", column="event_name").evaluate(connector)

        assert result.passed
        assert result.observed == 0

    def test_empty_table_reports_zero_nulls_not_an_error(
        self, connector: SqliteConnector
    ) -> None:
        # Surfaced decision: zero rows contain zero NULLs — the measure
        # is defined and exact, unlike DelayRule's valueless MAX. An
        # empty pipeline is the volume dimension's finding, not a
        # completeness error.
        result = NullCountRule(table="events", column="event_name").evaluate(connector)

        assert result.passed
        assert result.observed == 0

    def test_unusable_result_raises_rule_error(self) -> None:
        with pytest.raises(RuleError):
            NullCountRule(table="events", column="event_name").evaluate(
                NoRowsConnector()
            )

    def test_lower_layer_errors_propagate_unwrapped(
        self, connector: SqliteConnector
    ) -> None:
        with pytest.raises(DbError):
            NullCountRule(table="missing_table", column="event_name").evaluate(
                connector
            )

    @pytest.mark.parametrize("hostile", HOSTILE_IDENTIFIERS)
    def test_hostile_table_raises_sql_error(
        self, connector: SqliteConnector, hostile: str
    ) -> None:
        rule = NullCountRule(table=hostile, column="event_name")

        with pytest.raises(SqlError):
            rule.evaluate(connector)

    @pytest.mark.parametrize("hostile", HOSTILE_IDENTIFIERS)
    def test_hostile_column_raises_sql_error(
        self, connector: SqliteConnector, hostile: str
    ) -> None:
        rule = NullCountRule(table="events", column=hostile)

        with pytest.raises(SqlError):
            rule.evaluate(connector)


class TestNullCountTemplate:
    """Per-dialect assertions on the new packaged template (DoD clause)."""

    @pytest.mark.parametrize("dialect", list(DbType))
    def test_renders_quoted_identifiers_and_binds_nothing(
        self, dialect: DbType
    ) -> None:
        rendered = render_template(
            "null_count", dialect, {"table": "events", "column": "event_name"}
        )

        quote = "`" if dialect is DbType.MYSQL else '"'
        assert f"{quote}events{quote}" in rendered.sql
        assert f"{quote}event_name{quote}" in rendered.sql
        assert "IS NULL" in rendered.sql
        assert rendered.params == {}

    @pytest.mark.parametrize("dialect", list(DbType))
    @pytest.mark.parametrize("hostile", HOSTILE_IDENTIFIERS)
    def test_hostile_table_raises_per_dialect(
        self, dialect: DbType, hostile: str
    ) -> None:
        with pytest.raises(SqlError):
            render_template(
                "null_count", dialect, {"table": hostile, "column": "event_name"}
            )

    @pytest.mark.parametrize("dialect", list(DbType))
    @pytest.mark.parametrize("hostile", HOSTILE_IDENTIFIERS)
    def test_hostile_column_raises_per_dialect(
        self, dialect: DbType, hostile: str
    ) -> None:
        with pytest.raises(SqlError):
            render_template(
                "null_count", dialect, {"table": "events", "column": hostile}
            )
