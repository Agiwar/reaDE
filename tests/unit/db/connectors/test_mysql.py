"""Unit tests for MysqlConnector against a faked pymysql driver.

Driver behavior is faked at the module seam (the ``pymysql`` attribute of
the connector module), so every code path runs without a server. Real-server
behavior is asserted by the integration suite.
"""

import time
from types import TracebackType
from typing import Any, Self

import pytest

from reade.core.errors import DbError, NotConnectedError
from reade.core.interfaces import ConnectionInterface
from reade.db import MysqlConnector
from reade.db.connectors import mysql as mysql_module

# Static conformance proof: mypy verifies on this assignment that the
# implementation satisfies the protocol.
_conformance: ConnectionInterface = MysqlConnector(
    host="localhost", database="db", user="u", password="p"
)


class FakeMySQLError(Exception):
    pass


class FakeCursor:
    def __init__(self, rows: list[Any], description: object) -> None:
        self.rows = rows
        self.description = description
        self.executed: list[str] = []

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None

    def execute(self, sql: str) -> None:
        self.executed.append(sql)

    def fetchall(self) -> list[Any]:
        return self.rows


class FakeConnection:
    def __init__(self, cursor: FakeCursor) -> None:
        self._cursor = cursor
        self.closed = False

    def cursor(self) -> FakeCursor:
        return self._cursor

    def close(self) -> None:
        self.closed = True


class FakePymysql:
    MySQLError = FakeMySQLError

    def __init__(self, connection: FakeConnection) -> None:
        self.connection = connection
        self.connect_kwargs: dict[str, Any] | None = None
        self.connect_error: Exception | None = None

    def connect(self, **kwargs: Any) -> FakeConnection:
        if self.connect_error is not None:
            raise self.connect_error
        self.connect_kwargs = kwargs
        return self.connection


@pytest.fixture
def cursor() -> FakeCursor:
    return FakeCursor(rows=[(1, "a"), (2, "b")], description=("col",))


@pytest.fixture
def fake_pymysql(cursor: FakeCursor, monkeypatch: pytest.MonkeyPatch) -> FakePymysql:
    fake = FakePymysql(FakeConnection(cursor))
    monkeypatch.setattr(mysql_module, "pymysql", fake)
    return fake


@pytest.fixture
def connector(fake_pymysql: FakePymysql) -> MysqlConnector:
    return MysqlConnector(
        host="localhost",
        database="app",
        user="role",
        password="secret",  # pragma: allowlist secret
    )


class TestMissingDriver:
    def test_init_raises_import_error_naming_the_extra(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(mysql_module, "pymysql", None)

        with pytest.raises(ImportError, match=r"reade\[mysql\]"):
            MysqlConnector(host="h", database="d", user="u", password="p")


class TestConnect:
    def test_connect_passes_plain_parameters_to_driver(
        self, connector: MysqlConnector, fake_pymysql: FakePymysql
    ) -> None:
        connector.connect()

        assert fake_pymysql.connect_kwargs == {
            "host": "localhost",
            "port": 3306,
            "database": "app",
            "user": "role",
            "password": "secret",  # pragma: allowlist secret
            "autocommit": True,
        }

    def test_port_defaults_to_3306_and_is_overridable(
        self, fake_pymysql: FakePymysql
    ) -> None:
        connector = MysqlConnector(
            host="h", database="d", user="u", password="p", port=3307
        )
        connector.connect()

        assert fake_pymysql.connect_kwargs is not None
        assert fake_pymysql.connect_kwargs["port"] == 3307

    def test_connect_when_already_connected_is_a_noop(
        self, connector: MysqlConnector, fake_pymysql: FakePymysql
    ) -> None:
        connector.connect()
        fake_pymysql.connect_error = FakeMySQLError("must not be called again")

        connector.connect()

        assert connector.is_connected()

    def test_connect_failure_maps_to_db_error_with_cause(
        self, connector: MysqlConnector, fake_pymysql: FakePymysql
    ) -> None:
        fake_pymysql.connect_error = FakeMySQLError("refused")

        with pytest.raises(DbError) as exc_info:
            connector.connect()

        assert isinstance(exc_info.value.__cause__, FakeMySQLError)
        assert not connector.is_connected()

    def test_connect_timeout_passed_through_when_set(
        self, fake_pymysql: FakePymysql
    ) -> None:
        connector = MysqlConnector(
            host="h", database="d", user="u", password="p", connect_timeout=7
        )
        connector.connect()

        assert fake_pymysql.connect_kwargs is not None
        assert fake_pymysql.connect_kwargs["connect_timeout"] == 7

    def test_connect_attempts_below_one_raise_value_error(self) -> None:
        with pytest.raises(ValueError, match="connect_attempts"):
            MysqlConnector(
                host="h", database="d", user="u", password="p", connect_attempts=0
            )

    def test_connect_retries_transient_failures_then_succeeds(
        self, fake_pymysql: FakePymysql, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        sleeps: list[float] = []
        monkeypatch.setattr(time, "sleep", sleeps.append)
        failures = iter([FakeMySQLError("blip"), FakeMySQLError("blip")])
        original_connect = fake_pymysql.connect

        def flaky(**kwargs: Any) -> FakeConnection:
            for failure in failures:
                raise failure
            return original_connect(**kwargs)

        monkeypatch.setattr(fake_pymysql, "connect", flaky)
        connector = MysqlConnector(
            host="h",
            database="d",
            user="u",
            password="p",
            connect_attempts=3,
            retry_backoff=0.5,
        )

        connector.connect()

        assert connector.is_connected()
        assert sleeps == [0.5, 1.0]


class TestLifecycle:
    def test_close_is_idempotent_when_never_connected(
        self, connector: MysqlConnector
    ) -> None:
        connector.close()
        connector.close()

        assert not connector.is_connected()

    def test_close_is_idempotent_after_connect(self, connector: MysqlConnector) -> None:
        connector.connect()
        connector.close()
        connector.close()

        assert not connector.is_connected()

    def test_close_failure_maps_to_db_error(
        self, connector: MysqlConnector, fake_pymysql: FakePymysql
    ) -> None:
        def failing_close() -> None:
            raise FakeMySQLError("close failed")

        connector.connect()
        fake_pymysql.connection.close = failing_close  # type: ignore[method-assign]

        with pytest.raises(DbError):
            connector.close()

    def test_context_manager_connects_and_closes(
        self, connector: MysqlConnector, fake_pymysql: FakePymysql
    ) -> None:
        with connector as conn:
            assert conn.is_connected()

        assert not connector.is_connected()
        assert fake_pymysql.connection.closed

    def test_connection_raises_not_connected_before_connect(
        self, connector: MysqlConnector
    ) -> None:
        with pytest.raises(NotConnectedError):
            _ = connector.connection


class TestExecute:
    def test_execute_materializes_rows_as_tuples(
        self, connector: MysqlConnector
    ) -> None:
        connector.connect()

        rows = connector.execute("SELECT * FROM t")

        assert rows == [(1, "a"), (2, "b")]
        assert all(isinstance(row, tuple) for row in rows)

    def test_execute_returns_empty_list_when_no_result_set(
        self, connector: MysqlConnector, cursor: FakeCursor
    ) -> None:
        cursor.description = None
        cursor.rows = [("must", "not", "leak")]
        connector.connect()

        assert connector.execute("CREATE TABLE t (id INT)") == []

    def test_execute_when_not_connected_raises_not_connected(
        self, connector: MysqlConnector
    ) -> None:
        with pytest.raises(NotConnectedError):
            connector.execute("SELECT 1")

    def test_execute_failure_maps_to_db_error_with_cause(
        self, connector: MysqlConnector, cursor: FakeCursor
    ) -> None:
        def failing_execute(sql: str) -> None:
            raise FakeMySQLError("syntax error")

        cursor.execute = failing_execute  # type: ignore[method-assign]
        connector.connect()

        with pytest.raises(DbError) as exc_info:
            connector.execute("SELEC 1")

        assert isinstance(exc_info.value.__cause__, FakeMySQLError)


class TestPing:
    def test_ping_is_false_when_unconnected(self, connector: MysqlConnector) -> None:
        assert not connector.ping()

    def test_ping_round_trips_select_1(
        self, connector: MysqlConnector, cursor: FakeCursor
    ) -> None:
        connector.connect()

        assert connector.ping()
        assert cursor.executed == ["SELECT 1"]

    def test_ping_is_false_when_round_trip_fails(
        self, connector: MysqlConnector, cursor: FakeCursor
    ) -> None:
        def failing_execute(sql: str) -> None:
            raise FakeMySQLError("server closed the connection")

        connector.connect()
        cursor.execute = failing_execute  # type: ignore[method-assign]

        assert not connector.ping()
