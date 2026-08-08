"""Typed configuration models validated at the config boundary."""

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field


class SqliteConfig(BaseModel):
    """Validated connection configuration for SQLite.

    Field values map directly onto ``SqliteConnector`` parameters; unpack
    them at the call site — connectors take plain parameters, never models.

    Environment overrides are scoped: only ``READE__SQLITE__*`` variables
    apply to this model (``READE__SQLITE__DATABASE`` overrides
    ``database``), and variables outside the prefix — including bare
    ``READE__*`` ones — are ignored. Scoping is what lets several models
    share one process environment. Unknown fields, from the file or from
    within the prefix, are rejected with a field path.

    Attributes:
        database: Path to the SQLite database file, or ``:memory:``.

    Stability: stable.
    """

    model_config = ConfigDict(extra="forbid")

    env_prefix: ClassVar[str] = "SQLITE"

    database: str


class PostgresConfig(BaseModel):
    """Validated connection configuration for PostgreSQL.

    Field values map one-to-one onto ``PostgresConnector`` parameters;
    unpack them at the call site — connectors take plain parameters,
    never models.

    Environment overrides are scoped: only ``READE__POSTGRES__*``
    variables apply to this model (``READE__POSTGRES__HOST`` overrides
    ``host``), and variables outside the prefix — including bare
    ``READE__*`` ones — are ignored. Scoping is what lets several models
    share one process environment. Unknown fields, from the file or from
    within the prefix, are rejected with a field path.

    Attributes:
        host: Server hostname or IP address.
        database: Name of the database to connect to.
        user: Login role name.
        password: Login password.
        port: Server port. Defaults to PostgreSQL's standard 5432.
        connect_timeout: Per-attempt connection timeout in seconds;
            ``None`` keeps the driver default (libpq waits indefinitely).
        connect_attempts: Total connect() attempts; 1 means no retry.
        retry_backoff: Delay before the second attempt, in seconds;
            doubles after each subsequent failure.
        sslmode: libpq TLS mode (e.g. ``require``, ``verify-full``);
            ``None`` omits the option from the connector's driver call.
        sslrootcert: Path to the CA certificate file used to verify the
            server; ``None`` omits the option.
        sslcert: Path to the client certificate file; ``None`` omits
            the option.
        sslkey: Path to the client private key file; ``None`` omits
            the option.

    Stability: stable.
    """

    model_config = ConfigDict(extra="forbid")

    env_prefix: ClassVar[str] = "POSTGRES"

    host: str
    database: str
    user: str
    password: str = Field(repr=False)
    port: int = 5432
    connect_timeout: int | None = None
    connect_attempts: int = 1
    retry_backoff: float = 0.5
    sslmode: str | None = None
    sslrootcert: str | None = None
    sslcert: str | None = None
    sslkey: str | None = None


class MysqlConfig(BaseModel):
    """Validated connection configuration for MySQL/MariaDB.

    Field values map one-to-one onto ``MysqlConnector`` parameters;
    unpack them at the call site — connectors take plain parameters,
    never models.

    Environment overrides are scoped: only ``READE__MYSQL__*`` variables
    apply to this model (``READE__MYSQL__HOST`` overrides ``host``), and
    variables outside the prefix — including bare ``READE__*`` ones —
    are ignored. Scoping is what lets several models share one process
    environment. Unknown fields, from the file or from within the
    prefix, are rejected with a field path.

    Attributes:
        host: Server hostname or IP address.
        database: Name of the database to connect to.
        user: Login user name.
        password: Login password.
        port: Server port. Defaults to MySQL's standard 3306.
        connect_timeout: Per-attempt connection timeout in seconds;
            ``None`` keeps the driver default (pymysql uses 10 seconds).
        connect_attempts: Total connect() attempts; 1 means no retry.
        retry_backoff: Delay before the second attempt, in seconds;
            doubles after each subsequent failure.
        charset: Connection character set (e.g. ``utf8mb4``); ``None``
            omits the option from the connector's driver call.
        ssl_ca: Path to the CA certificate file used to verify the
            server; ``None`` omits the option.
        ssl_cert: Path to the client certificate file; ``None`` omits
            the option.
        ssl_key: Path to the client private key file; ``None`` omits
            the option.
        ssl_verify_cert: Verify the server certificate against the CA;
            ``False`` disables verification (forwarded, not omitted).
        ssl_verify_identity: Also verify that the server hostname
            matches the certificate; ``None`` omits the option.

    Stability: stable.
    """

    model_config = ConfigDict(extra="forbid")

    env_prefix: ClassVar[str] = "MYSQL"

    host: str
    database: str
    user: str
    password: str = Field(repr=False)
    port: int = 3306
    connect_timeout: int | None = None
    connect_attempts: int = 1
    retry_backoff: float = 0.5
    charset: str | None = None
    ssl_ca: str | None = None
    ssl_cert: str | None = None
    ssl_key: str | None = None
    ssl_verify_cert: bool | None = None
    ssl_verify_identity: bool | None = None
