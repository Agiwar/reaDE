"""Integration tests: the server-backed connectors against real servers.

These assert what the faked-driver unit suites cannot — actual driver
behavior on the wire: the empty-list clause for statements without result
sets, error mapping with real driver exceptions, the autocommit no-wedge
guarantee after a failed statement, and write durability across
close/reopen (the defect class the SQLite fix closed).

Setup: start the services and export the host variables —

    docker compose -f tests/integration/compose.yaml up -d --wait
    export READE_TEST_POSTGRES_HOST=127.0.0.1
    export READE_TEST_MYSQL_HOST=127.0.0.1
    uv run pytest -m integration

Each backend's tests skip with a clear reason when its variable is
absent, so the default ``make test`` stays zero-setup. CI sets both
variables and runs against service containers on every push — the gate
of record for the dockerized DoD item.
"""

import os
from typing import TYPE_CHECKING, Any

import pytest

from reade.core.errors import DbError
from reade.db import MysqlConnector, PostgresConnector

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from reade.core.base.connector import ConnectionBase

pytestmark = pytest.mark.integration

POSTGRES_HOST = os.environ.get("READE_TEST_POSTGRES_HOST")
MYSQL_HOST = os.environ.get("READE_TEST_MYSQL_HOST")

requires_postgres = pytest.mark.skipif(
    POSTGRES_HOST is None,
    reason="READE_TEST_POSTGRES_HOST not set; start tests/integration/compose.yaml",
)
requires_mysql = pytest.mark.skipif(
    MYSQL_HOST is None,
    reason="READE_TEST_MYSQL_HOST not set; start tests/integration/compose.yaml",
)


def _postgres() -> PostgresConnector:
    assert POSTGRES_HOST is not None
    return PostgresConnector(
        host=POSTGRES_HOST,
        database="reade",
        user="reade",
        password="reade",  # pragma: allowlist secret
        port=int(os.environ.get("READE_TEST_POSTGRES_PORT", "5432")),
        connect_timeout=5,
        connect_attempts=3,
    )


def _mysql() -> MysqlConnector:
    assert MYSQL_HOST is not None
    return MysqlConnector(
        host=MYSQL_HOST,
        database="reade",
        user="reade",
        password="reade",  # pragma: allowlist secret
        port=int(os.environ.get("READE_TEST_MYSQL_PORT", "3306")),
        connect_timeout=5,
        connect_attempts=3,
    )


BACKENDS = [
    pytest.param("postgres", marks=requires_postgres, id="postgres"),
    pytest.param("mysql", marks=requires_mysql, id="mysql"),
]


@pytest.fixture(params=BACKENDS)
def make_connector(
    request: pytest.FixtureRequest,
) -> "Callable[[], ConnectionBase[Any]]":
    factories: dict[str, Callable[[], ConnectionBase[Any]]] = {
        "postgres": _postgres,
        "mysql": _mysql,
    }
    return factories[request.param]


@pytest.fixture
def connector(
    make_connector: "Callable[[], ConnectionBase[Any]]",
) -> "Iterator[ConnectionBase[Any]]":
    instance = make_connector()
    yield instance
    instance.close()


class TestLifecycle:
    def test_connect_ping_close_roundtrip(
        self, connector: "ConnectionBase[Any]"
    ) -> None:
        assert not connector.is_connected()
        connector.connect()
        assert connector.is_connected()
        assert connector.ping()

        connector.close()
        connector.close()  # idempotent against a real server too

        assert not connector.is_connected()
        assert not connector.ping()


class TestExecuteContract:
    def test_select_returns_materialized_tuples(
        self, connector: "ConnectionBase[Any]"
    ) -> None:
        with connector:
            assert connector.execute("SELECT 1") == [(1,)]

    def test_statements_without_result_set_return_empty_list(
        self, connector: "ConnectionBase[Any]"
    ) -> None:
        # The frozen clause where driver variance lives: psycopg raises on
        # fetch-after-DDL, pymysql returns nothing — both must surface [].
        with connector:
            connector.execute("DROP TABLE IF EXISTS reade_it_empty")
            try:
                ddl = connector.execute("CREATE TABLE reade_it_empty (id INTEGER)")
                dml = connector.execute("INSERT INTO reade_it_empty VALUES (1)")

                assert ddl == []
                assert dml == []
            finally:
                connector.execute("DROP TABLE IF EXISTS reade_it_empty")

    def test_failing_statement_maps_to_db_error_and_does_not_wedge(
        self, connector: "ConnectionBase[Any]"
    ) -> None:
        with connector:
            with pytest.raises(DbError) as exc_info:
                connector.execute("SELECT * FROM reade_it_no_such_table")

            assert exc_info.value.__cause__ is not None
            # Autocommit guarantee: one failed statement must not poison
            # the connection for subsequent statements or health checks.
            assert connector.ping()
            assert connector.execute("SELECT 1") == [(1,)]


class TestDurability:
    def test_writes_survive_close_and_reopen(
        self, make_connector: "Callable[[], ConnectionBase[Any]]"
    ) -> None:
        # The recorded cross-backend semantic: each execute() is atomic
        # and immediately durable — nothing rolls back at close().
        with make_connector() as writer:
            writer.execute("DROP TABLE IF EXISTS reade_it_durability")
            writer.execute("CREATE TABLE reade_it_durability (id INTEGER)")
            writer.execute("INSERT INTO reade_it_durability VALUES (1)")

        try:
            with make_connector() as reader:
                count = reader.execute("SELECT COUNT(*) FROM reade_it_durability")

                assert count == [(1,)]
        finally:
            with make_connector() as cleanup:
                cleanup.execute("DROP TABLE IF EXISTS reade_it_durability")


class TestConnectFailure:
    @requires_postgres
    def test_postgres_bad_credentials_map_to_db_error(self) -> None:
        assert POSTGRES_HOST is not None
        connector = PostgresConnector(
            host=POSTGRES_HOST,
            database="reade",
            user="reade",
            password="wrong",  # pragma: allowlist secret
            connect_timeout=5,
        )

        with pytest.raises(DbError) as exc_info:
            connector.connect()

        assert exc_info.value.__cause__ is not None
        assert not connector.is_connected()

    @requires_mysql
    def test_mysql_bad_credentials_map_to_db_error(self) -> None:
        assert MYSQL_HOST is not None
        connector = MysqlConnector(
            host=MYSQL_HOST,
            database="reade",
            user="reade",
            password="wrong",  # pragma: allowlist secret
            connect_timeout=5,
        )

        with pytest.raises(DbError) as exc_info:
            connector.connect()

        assert exc_info.value.__cause__ is not None
        assert not connector.is_connected()
