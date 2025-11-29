"""Database metadata definitions and registry."""

from dataclasses import dataclass

from reade.core.enums.db_types import DBTypes


@dataclass(frozen=True)
class DBMetadata:
    """Static metadata for a database type."""

    db_type: DBTypes
    display_name: str
    default_port: int
    default_driver: str
    uri_scheme: str


DB_METADATA_MAP: dict[DBTypes, DBMetadata] = {
    DBTypes.POSTGRESQL: DBMetadata(
        db_type=DBTypes.POSTGRESQL,
        display_name="postgresql",
        default_port=5432,
        default_driver="psycopg2",
        uri_scheme="postgresql+psycopg2",
    ),
    DBTypes.MYSQL: DBMetadata(
        db_type=DBTypes.MYSQL,
        display_name="mysql",
        default_port=3306,
        default_driver="pymysql",
        uri_scheme="mysql+pymysql",
    ),
    DBTypes.SQLITE: DBMetadata(
        db_type=DBTypes.SQLITE,
        display_name="sqlite",
        default_port=0,
        default_driver="",
        uri_scheme="sqlite",
    ),
    DBTypes.TRINO: DBMetadata(
        db_type=DBTypes.TRINO,
        display_name="trino",
        default_port=8080,
        default_driver="",
        uri_scheme="trino",
    ),
}
