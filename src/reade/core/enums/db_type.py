"""Database type enumeration for supported databases."""

from enum import Enum


class DbType(str, Enum):
    """Supported database types.

    Attributes:
        SQLITE: SQLite file-based database.
        MYSQL: MySQL/MariaDB server.
        POSTGRESQL: PostgreSQL server.
    """

    SQLITE = "sqlite"
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"
