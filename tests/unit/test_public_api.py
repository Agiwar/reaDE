"""Smoke tests: the package imports and its public symbols are reachable."""

import reade
from reade.core.enums import DbType, FileType
from reade.core.errors import (
    ConfigError,
    DataIoError,
    DbError,
    DqError,
    NotConnectedError,
    ReadeError,
    RuleError,
    SqlError,
)
from reade.core.interfaces import ConfigLoader, ConnectionInterface
from reade.core.models import DB_METADATA_REGISTRY, DbMetadata


def test_package_is_importable() -> None:
    assert reade.__name__ == "reade"


def test_protocol_interfaces_are_importable() -> None:
    assert ConfigLoader is not None
    assert ConnectionInterface is not None


def test_module_errors_derive_from_reade_error() -> None:
    module_errors = (
        ConfigError,
        DataIoError,
        DbError,
        DqError,
        RuleError,
        SqlError,
    )
    assert all(issubclass(error, ReadeError) for error in module_errors)


def test_not_connected_error_derives_from_db_error() -> None:
    assert issubclass(NotConnectedError, DbError)


def test_db_types_cover_exactly_the_mvp_databases() -> None:
    assert set(DbType) == {DbType.SQLITE, DbType.MYSQL, DbType.POSTGRESQL}


def test_file_type_values_are_dotted_extensions() -> None:
    assert all(file_type.value.startswith(".") for file_type in FileType)


def test_metadata_registry_covers_every_db_type() -> None:
    assert set(DB_METADATA_REGISTRY) == set(DbType)
    assert all(
        isinstance(metadata, DbMetadata) for metadata in DB_METADATA_REGISTRY.values()
    )
