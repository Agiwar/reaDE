"""Unit tests for PostgresConnector against a faked psycopg driver.

Driver behavior is faked at the module seam (the ``psycopg`` attribute of
the connector module), so every code path runs without a server. Real-server
behavior — including psycopg's fetch-after-DDL error — is asserted by the
integration suite.
"""

from types import TracebackType
from typing import Any, Self

import pytest

from reade.core.errors import DbError, NotConnectedError
from reade.core.interfaces import ConnectionInterface
from reade.db import PostgresConnector
from reade.db.connectors import postgres as postgres_module

# Static conformance proof: mypy verifies on this assignment that the
# implementation satisfies the protocol.
_conformance: ConnectionInterface = PostgresConnector(
    host="localhost", database="db", user="u", password="p"
)


class FakePsycopgError(Exception):
    pass


class FakeCursor:
    """Cursor faking psycopg semantics: no description ⇒ fetch raises."""

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
        if self.description is None:
            raise FakePsycopgError("the last operation didn't produce a result")
        return self.rows


class FakeConnection:
    def __init__(self, cursor: FakeCursor) -> None:
        self._cursor = cursor
        self.closed = False
        self.executed: list[str] = []

    def cursor(self) -> FakeCursor:
        return self._cursor

    def execute(self, sql: str) -> None:
        self.executed.append(sql)

    def close(self) -> None:
        self.closed = True


class FakePsycopg:
    Error = FakePsycopgError

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
def fake_psycopg(cursor: FakeCursor, monkeypatch: pytest.MonkeyPatch) -> FakePsycopg:
    fake = FakePsycopg(FakeConnection(cursor))
    monkeypatch.setattr(postgres_module, "psycopg", fake)
    return fake


@pytest.fixture
def connector(fake_psycopg: FakePsycopg) -> PostgresConnector:
    return PostgresConnector(
        host="localhost",
        database="app",
        user="role",
        password="secret",  # pragma: allowlist secret
    )


class TestMissingDriver:
    def test_init_raises_import_error_naming_the_extra(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(postgres_module, "psycopg", None)

        with pytest.raises(ImportError, match=r"reade\[postgres\]"):
            PostgresConnector(host="h", database="d", user="u", password="p")


class TestConnect:
    def test_connect_passes_plain_parameters_to_driver(
        self, connector: PostgresConnector, fake_psycopg: FakePsycopg
    ) -> None:
        connector.connect()

        assert fake_psycopg.connect_kwargs == {
            "host": "localhost",
            "port": 5432,
            "dbname": "app",
            "user": "role",
            "password": "secret",  # pragma: allowlist secret
            "autocommit": True,
        }

    def test_port_defaults_to_5432_and_is_overridable(
        self, fake_psycopg: FakePsycopg
    ) -> None:
        connector = PostgresConnector(
            host="h", database="d", user="u", password="p", port=5433
        )
        connector.connect()

        assert fake_psycopg.connect_kwargs is not None
        assert fake_psycopg.connect_kwargs["port"] == 5433

    def test_connect_when_already_connected_is_a_noop(
        self, connector: PostgresConnector, fake_psycopg: FakePsycopg
    ) -> None:
        connector.connect()
        fake_psycopg.connect_error = FakePsycopgError("must not be called again")

        connector.connect()

        assert connector.is_connected()

    def test_connect_failure_maps_to_db_error_with_cause(
        self, connector: PostgresConnector, fake_psycopg: FakePsycopg
    ) -> None:
        fake_psycopg.connect_error = FakePsycopgError("refused")

        with pytest.raises(DbError) as exc_info:
            connector.connect()

        assert isinstance(exc_info.value.__cause__, FakePsycopgError)
        assert not connector.is_connected()


class TestLifecycle:
    def test_close_is_idempotent_when_never_connected(
        self, connector: PostgresConnector
    ) -> None:
        connector.close()
        connector.close()

        assert not connector.is_connected()

    def test_close_is_idempotent_after_connect(
        self, connector: PostgresConnector
    ) -> None:
        connector.connect()
        connector.close()
        connector.close()

        assert not connector.is_connected()

    def test_close_failure_maps_to_db_error(
        self, connector: PostgresConnector, fake_psycopg: FakePsycopg
    ) -> None:
        def failing_close() -> None:
            raise FakePsycopgError("close failed")

        connector.connect()
        fake_psycopg.connection.close = failing_close  # type: ignore[method-assign]

        with pytest.raises(DbError):
            connector.close()

    def test_context_manager_connects_and_closes(
        self, connector: PostgresConnector, fake_psycopg: FakePsycopg
    ) -> None:
        with connector as conn:
            assert conn.is_connected()

        assert not connector.is_connected()
        assert fake_psycopg.connection.closed

    def test_connection_raises_not_connected_before_connect(
        self, connector: PostgresConnector
    ) -> None:
        with pytest.raises(NotConnectedError):
            _ = connector.connection


class TestExecute:
    def test_execute_materializes_rows_as_tuples(
        self, connector: PostgresConnector
    ) -> None:
        connector.connect()

        rows = connector.execute("SELECT * FROM t")

        assert rows == [(1, "a"), (2, "b")]
        assert all(isinstance(row, tuple) for row in rows)

    def test_execute_returns_empty_list_when_no_result_set(
        self, connector: PostgresConnector, cursor: FakeCursor
    ) -> None:
        # psycopg raises on fetch after DDL/INSERT; description is the
        # no-result-set signal the connector must gate on.
        cursor.description = None
        connector.connect()

        assert connector.execute("CREATE TABLE t (id integer)") == []

    def test_execute_when_not_connected_raises_not_connected(
        self, connector: PostgresConnector
    ) -> None:
        with pytest.raises(NotConnectedError):
            connector.execute("SELECT 1")

    def test_execute_failure_maps_to_db_error_with_cause(
        self, connector: PostgresConnector, cursor: FakeCursor
    ) -> None:
        def failing_execute(sql: str) -> None:
            raise FakePsycopgError("syntax error")

        cursor.execute = failing_execute  # type: ignore[method-assign]
        connector.connect()

        with pytest.raises(DbError) as exc_info:
            connector.execute("SELEC 1")

        assert isinstance(exc_info.value.__cause__, FakePsycopgError)


class TestPing:
    def test_ping_is_false_when_unconnected(self, connector: PostgresConnector) -> None:
        assert not connector.ping()

    def test_ping_round_trips_select_1(
        self, connector: PostgresConnector, fake_psycopg: FakePsycopg
    ) -> None:
        connector.connect()

        assert connector.ping()
        assert fake_psycopg.connection.executed == ["SELECT 1"]

    def test_ping_is_false_when_round_trip_fails(
        self, connector: PostgresConnector, fake_psycopg: FakePsycopg
    ) -> None:
        def failing_execute(sql: str) -> None:
            raise FakePsycopgError("server closed the connection")

        connector.connect()
        fake_psycopg.connection.execute = failing_execute  # type: ignore[method-assign]

        assert not connector.ping()
