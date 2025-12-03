"""Database metadata registry."""

from dataclasses import dataclass

from reade.core.enums.db_types import DbType


@dataclass(frozen=True)
class DbMetadata:
    """Static metadata for a database type.

    Attributes:
        db_type: The database type enum value.
        display_name: Human-readable name.
        default_port: Default connection port (None for file-based DBs).
        default_driver: Default Python driver package.
        uri_scheme: SQLAlchemy URI scheme.
    """

    db_type: DbType
    display_name: str
    default_port: int | None
    default_driver: str
    uri_scheme: str


DB_METADATA_REGISTRY: dict[DbType, DbMetadata] = {
    DbType.SQLITE: DbMetadata(
        db_type=DbType.SQLITE,
        display_name="SQLite",
        default_port=None,
        default_driver="sqlite3",
        uri_scheme="sqlite",
    ),
    DbType.MYSQL: DbMetadata(
        db_type=DbType.MYSQL,
        display_name="MySQL",
        default_port=3306,
        default_driver="pymysql",
        uri_scheme="mysql+pymysql",
    ),
    DbType.POSTGRESQL: DbMetadata(
        db_type=DbType.POSTGRESQL,
        display_name="PostgreSQL",
        default_port=5432,
        default_driver="psycopg2",
        uri_scheme="postgresql+psycopg2",
    ),
}
