"""Configuration data models for validated config structures."""

from pydantic import BaseModel, Field, SecretStr


class DbCredentials(BaseModel):
    """Database connection credentials.

    Validates config loaded from YAML/JSON files. Use for PostgreSQL, MySQL,
    and other host-based databases.

    Attributes:
        host: Database server hostname or IP.
        port: Database server port (1-65535).
        database: Database name to connect to.
        username: Authentication username.
        password: Authentication password (masked in logs).

    Example:
        >>> config = get_config_content("db.yaml")
        >>> credentials = DbCredentials(**config)
        >>> credentials.password.get_secret_value()
        'actual_password'
    """

    model_config = {"extra": "forbid"}

    host: str
    port: int = Field(ge=1, le=65535)
    database: str
    username: str
    password: SecretStr


class SqliteCredentials(BaseModel):
    """SQLite database credentials.

    SQLite is file-based, so only requires the database path.

    Attributes:
        database: Path to the SQLite database file.

    Example:
        >>> config = get_config_content("sqlite.yaml")
        >>> credentials = SqliteCredentials(**config)
        >>> credentials.database
        '/path/to/data.db'
    """

    model_config = {"extra": "forbid"}

    database: str
