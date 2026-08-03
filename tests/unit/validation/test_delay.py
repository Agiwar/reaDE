"""Tests for DelayRule."""

from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta, timezone
from types import TracebackType
from typing import Any, Self

import pytest

from reade.core.enums import DbType
from reade.core.errors import RuleError, SqlError
from reade.data_io import execute_query
from reade.db import SqliteConnector
from reade.sql import render_template
from reade.validation import DelayRule

FIXED_NOW = datetime(2026, 8, 3, 12, 0, 0, tzinfo=UTC)
HOSTILE_IDENTIFIERS = ["events; DROP TABLE events", 'events"--']


class RowsConnector:
    """A protocol-only connector returning canned rows.

    Drives the normalizer's datetime/date branches that SQLite cannot
    reach — its driver returns timestamp columns as strings, while the
    server drivers return ``datetime`` objects.
    """

    db_type = DbType.SQLITE

    def __init__(self, rows: list[tuple[Any, ...]]) -> None:
        self._rows = rows

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
        return self._rows


@pytest.fixture
def connector() -> Iterator[SqliteConnector]:
    with SqliteConnector(database=":memory:") as conn:
        execute_query(conn, "CREATE TABLE events (event_name TEXT, created_at TEXT)")
        yield conn


def _insert(conn: SqliteConnector, value: str | None) -> None:
    execute_query(conn, "INSERT INTO events (created_at) VALUES (:v)", {"v": value})


def _rule(max_delay_seconds: float = 3600) -> DelayRule:
    return DelayRule(
        table="events",
        column="created_at",
        max_delay_seconds=max_delay_seconds,
        now=FIXED_NOW,
    )


class TestDelayRuleSqlite:
    """The string-timestamp path, against a real SQLite connection."""

    def test_fresh_passes_with_exact_observed_seconds(
        self, connector: SqliteConnector
    ) -> None:
        _insert(connector, "2026-08-03 11:59:00")

        result = _rule().evaluate(connector)

        assert result.passed
        assert result.rule == "delay"
        assert result.observed == 60.0
        assert result.threshold == 3600

    def test_stale_fails_as_result_not_exception(
        self, connector: SqliteConnector
    ) -> None:
        _insert(connector, "2026-08-03 09:00:00")

        result = _rule().evaluate(connector)

        assert not result.passed
        assert result.observed == 10800.0

    def test_newest_row_decides(self, connector: SqliteConnector) -> None:
        _insert(connector, "2026-08-01 00:00:00")
        _insert(connector, "2026-08-03 11:59:00")

        result = _rule().evaluate(connector)

        assert result.passed
        assert result.observed == 60.0

    def test_aware_string_normalizes_to_utc(self, connector: SqliteConnector) -> None:
        # 13:59 at +02:00 is 11:59 UTC — one minute before FIXED_NOW.
        _insert(connector, "2026-08-03 13:59:00+02:00")

        result = _rule().evaluate(connector)

        assert result.passed
        assert result.observed == 60.0

    def test_future_timestamp_yields_negative_delay_and_passes(
        self, connector: SqliteConnector
    ) -> None:
        _insert(connector, "2026-08-03 12:01:00")

        result = _rule().evaluate(connector)

        assert result.passed
        assert result.observed == -60.0

    def test_empty_table_raises_rule_error(self, connector: SqliteConnector) -> None:
        with pytest.raises(RuleError):
            _rule().evaluate(connector)

    def test_all_null_column_raises_rule_error(
        self, connector: SqliteConnector
    ) -> None:
        _insert(connector, None)

        with pytest.raises(RuleError):
            _rule().evaluate(connector)

    def test_unparseable_string_raises_rule_error_with_cause(
        self, connector: SqliteConnector
    ) -> None:
        _insert(connector, "not-a-timestamp")

        with pytest.raises(RuleError) as exc_info:
            _rule().evaluate(connector)

        assert isinstance(exc_info.value.__cause__, ValueError)

    @pytest.mark.parametrize("hostile", HOSTILE_IDENTIFIERS)
    def test_hostile_table_raises_sql_error(
        self, connector: SqliteConnector, hostile: str
    ) -> None:
        rule = DelayRule(table=hostile, column="created_at", max_delay_seconds=3600)

        with pytest.raises(SqlError):
            rule.evaluate(connector)

    @pytest.mark.parametrize("hostile", HOSTILE_IDENTIFIERS)
    def test_hostile_column_raises_sql_error(
        self, connector: SqliteConnector, hostile: str
    ) -> None:
        rule = DelayRule(table="events", column=hostile, max_delay_seconds=3600)

        with pytest.raises(SqlError):
            rule.evaluate(connector)

    def test_default_now_is_the_client_clock(self, connector: SqliteConnector) -> None:
        # No injected now: a just-inserted naive-UTC timestamp is fresh.
        _insert(
            connector,
            datetime.now(UTC).replace(tzinfo=None).isoformat(sep=" "),
        )

        result = DelayRule(
            table="events", column="created_at", max_delay_seconds=3600
        ).evaluate(connector)

        assert result.passed


class TestNormalizer:
    """Driver-shaped values, via a protocol-only canned connector."""

    def _observed(self, value: Any) -> float:
        result = DelayRule(
            table="events",
            column="created_at",
            max_delay_seconds=3600,
            now=FIXED_NOW,
        ).evaluate(RowsConnector([(value,)]))
        return result.observed

    def test_naive_datetime_is_assumed_utc(self) -> None:
        assert self._observed(datetime(2026, 8, 3, 11, 59, 0)) == 60.0

    def test_aware_datetime_converts_to_utc(self) -> None:
        plus_two = timezone(timedelta(hours=2))
        assert self._observed(datetime(2026, 8, 3, 13, 59, 0, tzinfo=plus_two)) == 60.0

    def test_date_becomes_midnight_utc(self) -> None:
        assert self._observed(date(2026, 8, 3)) == 43200.0

    def test_unsupported_type_raises_rule_error(self) -> None:
        with pytest.raises(RuleError):
            self._observed(1754222340)

    def test_rowless_result_raises_rule_error(self) -> None:
        with pytest.raises(RuleError):
            DelayRule(
                table="events",
                column="created_at",
                max_delay_seconds=3600,
                now=FIXED_NOW,
            ).evaluate(RowsConnector([]))

    def test_aware_now_argument_normalizes_like_values(self) -> None:
        plus_two = timezone(timedelta(hours=2))
        result = DelayRule(
            table="events",
            column="created_at",
            max_delay_seconds=3600,
            now=datetime(2026, 8, 3, 14, 0, 0, tzinfo=plus_two),  # 12:00 UTC
        ).evaluate(RowsConnector([(datetime(2026, 8, 3, 11, 59, 0),)]))

        assert result.observed == 60.0


class TestMaxTimestampTemplate:
    """Per-dialect assertions on the new packaged template (DoD clause)."""

    @pytest.mark.parametrize("dialect", list(DbType))
    def test_renders_quoted_identifiers_and_binds_nothing(
        self, dialect: DbType
    ) -> None:
        rendered = render_template(
            "max_timestamp", dialect, {"table": "events", "column": "created_at"}
        )

        quote = "`" if dialect is DbType.MYSQL else '"'
        assert f"{quote}events{quote}" in rendered.sql
        assert f"{quote}created_at{quote}" in rendered.sql
        assert rendered.params == {}

    @pytest.mark.parametrize("dialect", list(DbType))
    @pytest.mark.parametrize("hostile", HOSTILE_IDENTIFIERS)
    def test_hostile_table_raises_per_dialect(
        self, dialect: DbType, hostile: str
    ) -> None:
        with pytest.raises(SqlError):
            render_template(
                "max_timestamp", dialect, {"table": hostile, "column": "created_at"}
            )

    @pytest.mark.parametrize("dialect", list(DbType))
    @pytest.mark.parametrize("hostile", HOSTILE_IDENTIFIERS)
    def test_hostile_column_raises_per_dialect(
        self, dialect: DbType, hostile: str
    ) -> None:
        with pytest.raises(SqlError):
            render_template(
                "max_timestamp", dialect, {"table": "events", "column": hostile}
            )
