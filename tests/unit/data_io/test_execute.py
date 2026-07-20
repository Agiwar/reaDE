"""Tests for execute_query."""

from collections.abc import Iterator
from pathlib import Path

import pytest

from reade.core.errors import DbError, NotConnectedError
from reade.data_io import execute_query
from reade.db import SqliteConnector
from reade.sql import render_template


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

    def test_driver_failure_propagates_db_error_from_connector(
        self, connector: SqliteConnector
    ) -> None:
        with pytest.raises(DbError) as exc_info:
            execute_query(connector, "SELECT * FROM missing_table")

        assert exc_info.value.__cause__ is not None

    def test_unconnected_connector_passes_not_connected_error_through(self) -> None:
        with pytest.raises(NotConnectedError):
            execute_query(SqliteConnector(database=":memory:"), "SELECT 1")


class TestBoundParams:
    """The 2.2 seam: bound parameters flow through execute_query."""

    def test_bound_params_flow_through_the_seam(
        self, connector: SqliteConnector
    ) -> None:
        execute_query(connector, "CREATE TABLE t (id INTEGER, name TEXT)")
        execute_query(
            connector, "INSERT INTO t VALUES (:id, :name)", {"id": 1, "name": "a"}
        )

        rows = execute_query(connector, "SELECT name FROM t WHERE id = :id", {"id": 1})

        assert rows == [("a",)]

    def test_hostile_value_binds_through_the_full_sdk_path(
        self, connector: SqliteConnector, tmp_path: Path
    ) -> None:
        # The SQLite leg of the cross-dialect DoD injection test; the two
        # server dialects run the identical path in the integration suite.
        hostile = "1; DROP TABLE fact_orders;--"
        (tmp_path / "reflect_value.sql.j2").write_text(
            'SELECT {{ v | bind("v") }} AS v'
        )

        rendered = render_template(
            "reflect_value",
            connector.db_type,
            {"v": hostile},
            search_paths=[tmp_path],
        )
        rows = execute_query(connector, rendered.sql, rendered.params)

        assert hostile not in rendered.sql
        assert rows == [(hostile,)]
