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

The verified-TLS leg additionally needs the MySQL container's
auto-generated CA copied out —

    docker compose -f tests/integration/compose.yaml \
        cp mysql:/var/lib/mysql/ca.pem /tmp/mysql-ca.pem
    export READE_TEST_MYSQL_SSL_CA=/tmp/mysql-ca.pem

Each backend's tests skip with a clear reason when its variable is
absent, so the default ``make test`` stays zero-setup. CI sets both
variables and runs against service containers on every push — the gate
of record for the dockerized DoD item.
"""

import os
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import pytest

from reade.core.errors import DbError, RuleError
from reade.data_io import execute_query
from reade.db import MysqlConnector, PostgresConnector
from reade.sql import render_template
from reade.validation import DelayRule

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from pathlib import Path

    from reade.core.base.connector import ConnectionBase

pytestmark = pytest.mark.integration

POSTGRES_HOST = os.environ.get("READE_TEST_POSTGRES_HOST")
MYSQL_HOST = os.environ.get("READE_TEST_MYSQL_HOST")
MYSQL_SSL_CA = os.environ.get("READE_TEST_MYSQL_SSL_CA")

requires_postgres = pytest.mark.skipif(
    POSTGRES_HOST is None,
    reason="READE_TEST_POSTGRES_HOST not set; start tests/integration/compose.yaml",
)
requires_mysql = pytest.mark.skipif(
    MYSQL_HOST is None,
    reason="READE_TEST_MYSQL_HOST not set; start tests/integration/compose.yaml",
)
requires_mysql_ssl_ca = pytest.mark.skipif(
    MYSQL_SSL_CA is None,
    reason=(
        "READE_TEST_MYSQL_SSL_CA not set; copy the container's "
        "auto-generated CA out (see the module docstring)"
    ),
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


def _mysql(**overrides: Any) -> MysqlConnector:
    assert MYSQL_HOST is not None
    kwargs: dict[str, Any] = {
        "host": MYSQL_HOST,
        "database": "reade",
        "user": "reade",
        "password": "reade",  # pragma: allowlist secret
        "port": int(os.environ.get("READE_TEST_MYSQL_PORT", "3306")),
        "connect_timeout": 5,
        "connect_attempts": 3,
    }
    kwargs.update(overrides)
    return MysqlConnector(**kwargs)


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


class TestBoundParams:
    """The 2.2 execute seam against real drivers on the wire."""

    def test_hostile_value_binds_through_the_full_sdk_path(
        self, connector: "ConnectionBase[Any]", tmp_path: "Path"
    ) -> None:
        # Cross-dialect DoD leg: render → bind → RenderedQuery →
        # execute_query. The value must travel as a parameter, never in
        # the SQL text; SQLite runs the identical path in the unit suite.
        hostile = "1; DROP TABLE fact_orders;--"
        (tmp_path / "reflect_value.sql.j2").write_text(
            'SELECT {{ v | bind("v") }} AS v'
        )

        with connector:
            rendered = render_template(
                "reflect_value",
                connector.db_type,
                {"v": hostile},
                search_paths=[tmp_path],
            )
            rows = execute_query(connector, rendered.sql, rendered.params)

        assert hostile not in rendered.sql
        assert rows == [(hostile,)]

    def test_literal_percent_survives_empty_params_at_the_seam(
        self, connector: "ConnectionBase[Any]"
    ) -> None:
        # Ruled regression (2.2 kickoff): pyformat drivers %-format the
        # statement whenever parameters are present, so the connector must
        # normalize an empty mapping to None or a literal % corrupts.
        # Asserted on both pyformat backends only — SQLite is exempt: its
        # named placeholder style never %-formats, so the test would be
        # vacuous there.
        with connector:
            assert execute_query(connector, "SELECT '100%'", {}) == [("100%",)]

    def test_bound_param_insert_is_durable(
        self, make_connector: "Callable[[], ConnectionBase[Any]]"
    ) -> None:
        # The D9 durability semantic, now through the params path.
        with make_connector() as writer:
            writer.execute("DROP TABLE IF EXISTS reade_it_params")
            writer.execute("CREATE TABLE reade_it_params (v VARCHAR(64))")
            writer.execute("INSERT INTO reade_it_params VALUES (%(v)s)", {"v": "bound"})

        try:
            with make_connector() as reader:
                count = reader.execute("SELECT COUNT(*) FROM reade_it_params")

                assert count == [(1,)]
        finally:
            with make_connector() as cleanup:
                cleanup.execute("DROP TABLE IF EXISTS reade_it_params")


class TestDelayRule:
    """The 3.1 delay rule against real drivers on the wire.

    Timestamp columns arrive as ``datetime`` objects from both server
    drivers, not the strings SQLite returns — the normalizer leg the
    unit suite reaches only with canned fakes.
    """

    def test_fresh_timestamp_passes_via_driver_datetime(
        self, connector: "ConnectionBase[Any]"
    ) -> None:
        # The timestamp is inserted from the client clock as naive UTC,
        # so the measured delay is independent of the server clock.
        with connector:
            connector.execute("DROP TABLE IF EXISTS reade_it_delay")
            try:
                connector.execute("CREATE TABLE reade_it_delay (created_at TIMESTAMP)")
                connector.execute(
                    "INSERT INTO reade_it_delay VALUES (%(ts)s)",
                    {"ts": datetime.now(UTC).replace(tzinfo=None)},
                )
                value = connector.execute("SELECT MAX(created_at) FROM reade_it_delay")[
                    0
                ][0]
                assert isinstance(value, datetime)  # the wire divergence

                result = DelayRule(
                    table="reade_it_delay",
                    column="created_at",
                    max_delay_seconds=3600,
                ).evaluate(connector)

                assert result.passed
                assert result.rule == "delay"
            finally:
                connector.execute("DROP TABLE IF EXISTS reade_it_delay")

    def test_empty_table_raises_rule_error(
        self, connector: "ConnectionBase[Any]"
    ) -> None:
        with connector:
            connector.execute("DROP TABLE IF EXISTS reade_it_delay_empty")
            try:
                connector.execute(
                    "CREATE TABLE reade_it_delay_empty (created_at TIMESTAMP)"
                )
                with pytest.raises(RuleError):
                    DelayRule(
                        table="reade_it_delay_empty",
                        column="created_at",
                        max_delay_seconds=3600,
                    ).evaluate(connector)
            finally:
                connector.execute("DROP TABLE IF EXISTS reade_it_delay_empty")


class TestTls:
    """The 4.2 TLS options against the dockerized MySQL server.

    MySQL 8 auto-generates server certificates at initialization, so the
    stock container negotiates TLS with no fixture provisioning; the
    verified leg only needs the auto-generated CA copied out of the
    container (CI does this in a workflow step). pymysql attempts
    opportunistic TLS even with no options set, so the discriminating
    assertions are about verification: a verified session using the CA,
    and a loud handshake failure when verification is required against
    a CA the client does not trust.
    """

    @requires_mysql
    @requires_mysql_ssl_ca
    def test_mysql_verified_tls_session_with_shipped_options(self) -> None:
        with _mysql(ssl_ca=MYSQL_SSL_CA, ssl_verify_cert=True) as connector:
            rows = connector.execute("SHOW STATUS LIKE 'Ssl_cipher'")

        assert rows, "session status query returned nothing"
        assert rows[0][1] != "", "TLS was not negotiated (empty Ssl_cipher)"

    @requires_mysql
    def test_mysql_tls_verification_enforced_without_trusted_ca(self) -> None:
        # Positive control: the same server accepts a plain connection,
        # so the failure below is attributable to certificate
        # verification, not availability — without it, this test's
        # assertions cannot tell a rejected handshake from a down server.
        with _mysql() as control:
            assert control.is_connected()

        # ssl_verify_cert=True with no CA verifies against the system
        # trust store, which cannot vouch for the container's
        # auto-generated certificate — the handshake must fail loudly,
        # proving the forwarded option governs real verification.
        connector = _mysql(ssl_verify_cert=True, connect_attempts=1)

        with pytest.raises(DbError) as exc_info:
            connector.connect()

        assert exc_info.value.__cause__ is not None
        assert not connector.is_connected()


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
