"""Tests for the private dialect registry."""

from reade.core.enums import DbType
from reade.sql._dialect import _DIALECTS


def test_dialect_registry_covers_every_db_type() -> None:
    assert set(_DIALECTS) == set(DbType)


def test_placeholder_styles_match_the_driver_paramstyles() -> None:
    assert _DIALECTS[DbType.SQLITE].placeholder("k") == ":k"
    assert _DIALECTS[DbType.MYSQL].placeholder("k") == "%(k)s"
    assert _DIALECTS[DbType.POSTGRESQL].placeholder("k") == "%(k)s"


def test_quoting_characters_match_the_dialects() -> None:
    assert _DIALECTS[DbType.SQLITE].quote_char == '"'
    assert _DIALECTS[DbType.POSTGRESQL].quote_char == '"'
    assert _DIALECTS[DbType.MYSQL].quote_char == "`"
