"""Typed configuration models validated at the config boundary."""

from typing import ClassVar

from pydantic import BaseModel, ConfigDict


class SqliteConfig(BaseModel):
    """Validated connection configuration for SQLite.

    Field values map directly onto ``SqliteConnector`` parameters; unpack
    them at the call site — connectors take plain parameters, never models.

    Unknown fields are rejected (``extra="forbid"``), so a typo'd key — in
    a config file or an environment override — fails validation with a
    field path instead of being silently ignored.

    Attributes:
        database: Path to the SQLite database file, or ``:memory:``.
    """

    model_config = ConfigDict(extra="forbid")

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
    """

    model_config = ConfigDict(extra="forbid")

    env_prefix: ClassVar[str] = "POSTGRES"

    host: str
    database: str
    user: str
    password: str
    port: int = 5432


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
    """

    model_config = ConfigDict(extra="forbid")

    env_prefix: ClassVar[str] = "MYSQL"

    host: str
    database: str
    user: str
    password: str
    port: int = 3306
