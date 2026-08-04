"""Tests for CompletenessDimension."""

from collections.abc import Iterator

import pytest

from reade.core.errors import DqError, SqlError
from reade.data_io import execute_query
from reade.db import SqliteConnector
from reade.dq import CompletenessDimension


@pytest.fixture
def connector() -> Iterator[SqliteConnector]:
    with SqliteConnector(database=":memory:") as conn:
        execute_query(conn, "CREATE TABLE events (event_name TEXT, city TEXT)")
        yield conn


class TestCompletenessDimension:
    def test_aggregates_passing_rules(self, connector: SqliteConnector) -> None:
        execute_query(
            connector,
            "INSERT INTO events VALUES ('signup', 'tokyo'), ('login', 'osaka')",
        )

        result = CompletenessDimension(
            table="events", columns=["event_name", "city"]
        ).assess(connector)

        assert result.dimension == "completeness"
        assert result.passed
        assert len(result.rule_results) == 2
        assert all(rule.rule == "null_count" for rule in result.rule_results)

    def test_rule_results_follow_columns_order(
        self, connector: SqliteConnector
    ) -> None:
        # The first shipped plural: outcomes are reported in the
        # constructor's column order, asserted via distinguishable
        # observed counts (event_name fully populated, city one NULL).
        execute_query(
            connector,
            "INSERT INTO events VALUES ('signup', 'tokyo'), ('login', NULL)",
        )

        forward = CompletenessDimension(
            table="events", columns=["event_name", "city"], max_nulls=1
        ).assess(connector)
        swapped = CompletenessDimension(
            table="events", columns=["city", "event_name"], max_nulls=1
        ).assess(connector)

        assert [rule.observed for rule in forward.rule_results] == [0, 1]
        assert [rule.observed for rule in swapped.rule_results] == [1, 0]

    def test_fails_as_result_when_any_column_fails(
        self, connector: SqliteConnector
    ) -> None:
        # passed = all columns; the failing column is visible in the
        # plural rule_results next to the passing one.
        execute_query(
            connector,
            "INSERT INTO events VALUES ('signup', 'tokyo'), ('login', NULL)",
        )

        result = CompletenessDimension(
            table="events", columns=["event_name", "city"]
        ).assess(connector)

        assert not result.passed
        assert result.rule_results[0].passed
        assert not result.rule_results[1].passed

    def test_uniform_threshold_applies_to_every_column(
        self, connector: SqliteConnector
    ) -> None:
        # One max_nulls for all columns, by ruling; per-column tuning
        # is another dimension instance.
        execute_query(
            connector,
            "INSERT INTO events VALUES"
            " ('signup', NULL), (NULL, NULL), ('login', 'osaka')",
        )

        result = CompletenessDimension(
            table="events", columns=["event_name", "city"], max_nulls=1
        ).assess(connector)

        assert not result.passed
        assert result.rule_results[0].passed  # event_name: 1 NULL <= 1
        assert not result.rule_results[1].passed  # city: 2 NULLs > 1

    def test_empty_table_reports_zero_nulls_not_an_error(
        self, connector: SqliteConnector
    ) -> None:
        # The aggregate-NULL principle at the dimension layer: COUNT
        # over zero rows is a defined, exact 0 — a result, not a raise.
        # An empty pipeline is the volume dimension's finding;
        # composing the two verdicts is check's job.
        result = CompletenessDimension(
            table="events", columns=["event_name", "city"]
        ).assess(connector)

        assert result.passed
        assert [rule.observed for rule in result.rule_results] == [0, 0]

    def test_empty_columns_is_a_caller_bug(self) -> None:
        # Zero rules would make a vacuously passing report row —
        # measuring nothing and reporting complete is the misreporting
        # class the SDK refuses. Loud at the typo site, before any
        # connector is involved.
        with pytest.raises(DqError):
            CompletenessDimension(table="events", columns=[])

    def test_bare_string_columns_is_a_caller_bug(self) -> None:
        # A str satisfies Sequence[str] structurally; iterating it
        # would build per-character rules and fail as baffling
        # unknown-column errors at assess time. Refused loudly instead.
        with pytest.raises(DqError):
            CompletenessDimension(table="events", columns="event_name")

    def test_hostile_identifier_raises_sql_error_through_the_dimension(
        self, connector: SqliteConnector
    ) -> None:
        # A hostile identifier in a dimension is a caller bug, not a
        # data condition: SqlError raises at render, propagates through
        # assess, and never reaches the database.
        dimension = CompletenessDimension(
            table="events", columns=["city; DROP TABLE events"]
        )

        with pytest.raises(SqlError):
            dimension.assess(connector)
