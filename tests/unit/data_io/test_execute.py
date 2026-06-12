"""Tests for execute_query."""

from collections.abc import Iterator

import pytest

from reade.core.errors import DataIoError, NotConnectedError
from reade.data_io import execute_query
from reade.db import SqliteConnector


@pytest.fixture
def connector() -> Iterator[SqliteConnector]:
    with SqliteConnector(database=":memory:") as conn:
        yield conn


class TestExecuteQuery:
    def test_select_returns_rows_as_tuples(self, connector: SqliteConnector) -> None:
        execute_query(connector, "CREATE TABLE t (id INTEGER, name TEXT)")
        execute_query(connector, "INSERT INTO t VALUES (1, 'a'), (2, 'b')")

        rows = execute_query(connector, "SELECT id, name FROM t ORDER BY id")

        assert rows == [(1, "a"), (2, "b")]

    def test_statement_without_result_set_returns_empty_list(
        self, connector: SqliteConnector
    ) -> None:
        assert execute_query(connector, "CREATE TABLE t (id INTEGER)") == []

    def test_driver_failure_raises_data_io_error_with_cause(
        self, connector: SqliteConnector
    ) -> None:
        with pytest.raises(DataIoError) as exc_info:
            execute_query(connector, "SELECT * FROM missing_table")

        assert exc_info.value.__cause__ is not None

    def test_unconnected_connector_passes_not_connected_error_through(self) -> None:
        with pytest.raises(NotConnectedError):
            execute_query(SqliteConnector(database=":memory:"), "SELECT 1")
