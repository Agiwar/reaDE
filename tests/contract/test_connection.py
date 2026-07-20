"""Contract tests for the ConnectionInterface protocol.

Every connector implementation must satisfy these guarantees, in
particular close() idempotency: closing an unconnected or already-closed
connection is a no-op. The protocol-only connector below is the
plug-in-promise contract: a structural implementation that inherits
nothing from reaDE must pass every consumer seam.
"""

import sqlite3
from types import TracebackType
from typing import Any, Self

import pytest

from reade.core.enums import DbType
from reade.core.errors import NotConnectedError
from reade.core.interfaces import ConnectionInterface
from reade.data_io import execute_query
from reade.db import MysqlConnector, PostgresConnector, SqliteConnector
from reade.dq import VolumeDimension
from reade.validation import RowCountRule

# Static conformance proof: mypy verifies on this assignment that the
# implementation satisfies the protocol.
_conformance: ConnectionInterface = SqliteConnector(database=":memory:")


class ProtocolOnlyConnector:
    """A third-party-style connector satisfying the protocol structurally.

    Inherits nothing from reaDE. ``db_type`` is a plain class attribute —
    the protocol's read-only property member must accept it, or
    per-instance-dialect plug-ins would be barred from the seams.
    """

    db_type = DbType.SQLITE

    def __init__(self) -> None:
        self._connection: sqlite3.Connection | None = None

    def __enter__(self) -> Self:
        self.connect()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def connect(self) -> None:
        if self._connection is None:
            self._connection = sqlite3.connect(":memory:", autocommit=True)

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def is_connected(self) -> bool:
        return self._connection is not None

    def ping(self) -> bool:
        if self._connection is None:
            return False
        self._connection.execute("SELECT 1")
        return True

    def execute(
        self, sql: str, params: dict[str, Any] | None = None
    ) -> list[tuple[Any, ...]]:
        if not params:  # the interface's documented falsy-to-None promise
            params = None
        assert self._connection is not None
        cursor = (
            self._connection.execute(sql)
            if params is None
            else self._connection.execute(sql, params)
        )
        return [tuple(row) for row in cursor.fetchall()]


# Static conformance proof for the plug-in case: a protocol-only
# implementation with a plain-attribute db_type satisfies the protocol.
_protocol_only: ConnectionInterface = ProtocolOnlyConnector()


def _read_db_type(connector: ConnectionInterface) -> DbType:
    """Static proof that db_type is readable through the protocol type."""
    return connector.db_type


@pytest.fixture
def connector() -> SqliteConnector:
    return SqliteConnector(database=":memory:")


class TestConnectionContract:
    def test_close_is_idempotent_when_never_connected(
        self, connector: SqliteConnector
    ) -> None:
        connector.close()
        connector.close()

        assert not connector.is_connected()

    def test_close_is_idempotent_after_connect(
        self, connector: SqliteConnector
    ) -> None:
        connector.connect()
        connector.close()
        connector.close()

        assert not connector.is_connected()

    def test_context_manager_connects_and_closes(
        self, connector: SqliteConnector
    ) -> None:
        with connector as conn:
            assert conn.is_connected()
            assert conn.ping()

        assert not connector.is_connected()

    def test_is_connected_tracks_lifecycle(self, connector: SqliteConnector) -> None:
        assert not connector.is_connected()
        connector.connect()
        assert connector.is_connected()
        connector.close()
        assert not connector.is_connected()

    def test_ping_is_false_when_unconnected(self, connector: SqliteConnector) -> None:
        assert not connector.ping()

    def test_connection_raises_not_connected_before_connect(
        self, connector: SqliteConnector
    ) -> None:
        with pytest.raises(NotConnectedError):
            _ = connector.connection

    def test_connection_raises_not_connected_after_close(
        self, connector: SqliteConnector
    ) -> None:
        connector.connect()
        connector.close()

        with pytest.raises(NotConnectedError):
            _ = connector.connection

    def test_every_connector_declares_its_db_type(self) -> None:
        connectors = (SqliteConnector, PostgresConnector, MysqlConnector)

        assert {connector.db_type for connector in connectors} == set(DbType)


class TestProtocolPluginPromise:
    """A protocol-only connector must pass every consumer seam."""

    def test_seams_accept_a_protocol_only_connector(self) -> None:
        with ProtocolOnlyConnector() as connector:
            execute_query(connector, "CREATE TABLE events (event_name TEXT)")
            execute_query(
                connector,
                "INSERT INTO events VALUES (:name)",
                {"name": "signup"},
            )

            assert _read_db_type(connector) is DbType.SQLITE
            rule_result = RowCountRule(table="events", min_rows=1).evaluate(connector)
            dq_result = VolumeDimension(table="events", min_rows=1).assess(connector)

        assert rule_result.passed
        assert dq_result.passed
