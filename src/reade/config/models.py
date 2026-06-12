"""Typed configuration models validated at the config boundary."""

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
