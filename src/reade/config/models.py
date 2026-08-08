"""Typed configuration models validated at the config boundary."""

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

from reade.config._uri import expand_uri
from reade.core.enums.db_type import DbType


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

    URI input: a ``uri`` key — in the file or as ``READE__SQLITE__URI``
    — expands before validation into ``database``
    (``sqlite:///path.db``; ``sqlite:////abs/path.db`` for absolute
    paths; ``sqlite:///:memory:`` works). Setting ``uri`` together with
    ``database`` raises ``ConfigError``; sqlite URIs take no host and
    no query parameters. The model never retains the URI string, and
    typed callers pass ``uri`` in the input mapping (``model_validate``,
    file, or env) — the synthesized constructor signature knows only
    real fields.

    Attributes:
        database: Path to the SQLite database file, or ``:memory:``.

    Stability: stable.
    """

    model_config = ConfigDict(extra="forbid")

    env_prefix: ClassVar[str] = "SQLITE"

    database: str

    @model_validator(mode="before")
    @classmethod
    def _expand_uri(cls, data: object) -> object:
        """Expand a ``uri`` input key before field validation."""
        if isinstance(data, dict):
            return expand_uri(data, db_type=DbType.SQLITE)
        return data


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

    URI input: a ``uri`` key — in the file or as
    ``READE__POSTGRES__URI`` — expands before validation into ``host``,
    ``port``, ``user``, ``password``, and ``database`` (``postgresql://``
    followed by ``user:password@host:port/database``; credentials
    percent-decoded; port optional, defaulting like the field). Setting
    ``uri`` together with any of those keys raises ``ConfigError``,
    while option fields compose beside a URI. Allowlisted query
    parameters map onto this model's option fields (``sslmode``,
    ``sslrootcert``, ``sslcert``, ``sslkey``); unknown keys are
    rejected. The model never retains the URI string, and typed callers
    pass ``uri`` in the input mapping (``model_validate``, file, or
    env) — the synthesized constructor signature knows only real
    fields.

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

    @model_validator(mode="before")
    @classmethod
    def _expand_uri(cls, data: object) -> object:
        """Expand a ``uri`` input key before field validation."""
        if isinstance(data, dict):
            return expand_uri(data, db_type=DbType.POSTGRESQL)
        return data


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

    URI input: a ``uri`` key — in the file or as ``READE__MYSQL__URI``
    — expands before validation into ``host``, ``port``, ``user``,
    ``password``, and ``database`` (``mysql://`` followed by
    ``user:password@host:port/database``; credentials percent-decoded;
    port optional, defaulting like the field). Setting ``uri`` together
    with any of those keys raises ``ConfigError``, while option fields
    compose beside a URI. Allowlisted query parameters map onto this
    model's option fields (``charset``, ``ssl_ca``, ``ssl_cert``,
    ``ssl_key``, ``ssl_verify_cert``, ``ssl_verify_identity``); unknown
    keys are rejected. The model never retains the URI string, and
    typed callers pass ``uri`` in the input mapping (``model_validate``,
    file, or env) — the synthesized constructor signature knows only
    real fields.

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
            Effective only together with ``ssl_ca`` — without a CA,
            pymysql forces hostname checking off.

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

    @model_validator(mode="before")
    @classmethod
    def _expand_uri(cls, data: object) -> object:
        """Expand a ``uri`` input key before field validation."""
        if isinstance(data, dict):
            return expand_uri(data, db_type=DbType.MYSQL)
        return data
