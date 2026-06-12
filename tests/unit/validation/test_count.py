"""Tests for RowCountRule."""

from collections.abc import Iterator

import pytest

from reade.core.errors import DataIoError
from reade.data_io import execute_query
from reade.db import SqliteConnector
from reade.validation import RowCountRule


@pytest.fixture
def connector() -> Iterator[SqliteConnector]:
    with SqliteConnector(database=":memory:") as conn:
        execute_query(conn, "CREATE TABLE events (id INTEGER)")
        execute_query(conn, "INSERT INTO events VALUES (1), (2), (3)")
        yield conn


class TestRowCountRule:
    def test_passes_when_count_meets_threshold(
        self, connector: SqliteConnector
    ) -> None:
        result = RowCountRule(table="events", min_rows=3).evaluate(connector)

        assert result.passed
        assert result.rule == "row_count"
        assert result.observed == 3
        assert result.threshold == 3

    def test_fails_as_result_not_exception_when_below_threshold(
        self, connector: SqliteConnector
    ) -> None:
        result = RowCountRule(table="events", min_rows=10).evaluate(connector)

        assert not result.passed
        assert result.observed == 3

    def test_lower_layer_errors_propagate_unwrapped(
        self, connector: SqliteConnector
    ) -> None:
        with pytest.raises(DataIoError):
            RowCountRule(table="missing_table").evaluate(connector)
