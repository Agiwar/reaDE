"""Tests for VolumeDimension."""

from collections.abc import Iterator

import pytest

from reade.data_io import execute_query
from reade.db import SqliteConnector
from reade.dq import VolumeDimension


@pytest.fixture
def connector() -> Iterator[SqliteConnector]:
    with SqliteConnector(database=":memory:") as conn:
        execute_query(conn, "CREATE TABLE events (id INTEGER)")
        execute_query(conn, "INSERT INTO events VALUES (1), (2)")
        yield conn


class TestVolumeDimension:
    def test_aggregates_passing_rule(self, connector: SqliteConnector) -> None:
        result = VolumeDimension(table="events", min_rows=1).assess(connector)

        assert result.dimension == "volume"
        assert result.passed
        assert len(result.rule_results) == 1
        assert result.rule_results[0].rule == "row_count"

    def test_fails_as_result_when_rule_fails(self, connector: SqliteConnector) -> None:
        result = VolumeDimension(table="events", min_rows=10).assess(connector)

        assert not result.passed
        assert not result.rule_results[0].passed
