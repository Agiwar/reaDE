"""Contract tests for the ConnectionInterface protocol.

Every connector implementation must satisfy these guarantees, in
particular close() idempotency: closing an unconnected or already-closed
connection is a no-op.
"""

import pytest

from reade.core.errors import NotConnectedError
from reade.core.interfaces import ConnectionInterface
from reade.db import SqliteConnector

# Static conformance proof: mypy verifies on this assignment that the
# implementation satisfies the protocol.
_conformance: ConnectionInterface = SqliteConnector(database=":memory:")


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
