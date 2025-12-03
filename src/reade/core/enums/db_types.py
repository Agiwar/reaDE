"""Database type enumeration."""

from enum import Enum


class DBTypes(str, Enum):
    """Supported database types."""

    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLITE = "sqlite"
