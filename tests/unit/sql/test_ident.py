"""Tests for the ident filter: allowlist validation and dialect quoting."""

from pathlib import Path
from typing import Any

import pytest
from jinja2 import UndefinedError

from reade.core.enums import DbType
from reade.core.errors import SqlError
from reade.sql import RenderedQuery, render_template

DOD_HOSTILE_IDENTIFIERS = [
    "fact_orders; DROP TABLE fact_orders",
    'fact_orders"--',
]


def _render_ident(
    tmp_path: Path, value: Any, dialect: DbType = DbType.SQLITE
) -> RenderedQuery:
    (tmp_path / "t.sql.j2").write_text("FROM {{ table | ident }}", encoding="utf-8")
    return render_template("t", dialect, {"table": value}, search_paths=[tmp_path])


class TestIdentQuoting:
    @pytest.mark.parametrize(
        ("dialect", "expected"),
        [
            (DbType.SQLITE, 'FROM "events"'),
            (DbType.MYSQL, "FROM `events`"),
            (DbType.POSTGRESQL, 'FROM "events"'),
        ],
    )
    def test_quotes_identifier_per_dialect(
        self, dialect: DbType, expected: str, tmp_path: Path
    ) -> None:
        rendered = _render_ident(tmp_path, "events", dialect)

        assert rendered.sql == expected
        assert rendered.params == {}

    @pytest.mark.parametrize(
        ("dialect", "expected"),
        [
            (DbType.SQLITE, 'FROM "analytics"."events"'),
            (DbType.MYSQL, "FROM `analytics`.`events`"),
            (DbType.POSTGRESQL, 'FROM "analytics"."events"'),
        ],
    )
    def test_quotes_each_part_of_a_schema_qualified_identifier(
        self, dialect: DbType, expected: str, tmp_path: Path
    ) -> None:
        rendered = _render_ident(tmp_path, "analytics.events", dialect)

        assert rendered.sql == expected

    def test_mixed_case_identifier_is_quoted_exact(self, tmp_path: Path) -> None:
        rendered = _render_ident(tmp_path, "Events", DbType.POSTGRESQL)

        assert rendered.sql == 'FROM "Events"'

    def test_reserved_word_is_allowed_because_quoting_disarms_it(
        self, tmp_path: Path
    ) -> None:
        rendered = _render_ident(tmp_path, "select", DbType.SQLITE)

        assert rendered.sql == 'FROM "select"'


class TestIdentRejection:
    @pytest.mark.parametrize("hostile", DOD_HOSTILE_IDENTIFIERS)
    @pytest.mark.parametrize("dialect", list(DbType))
    def test_dod_hostile_identifiers_raise(
        self, hostile: str, dialect: DbType, tmp_path: Path
    ) -> None:
        with pytest.raises(SqlError, match="not allowed"):
            _render_ident(tmp_path, hostile, dialect)

    @pytest.mark.parametrize(
        "hostile",
        [
            "",
            "a.",
            ".a",
            "a..b",
            "db.schema.table",
            "0abc",
            "café",
            "tab\u200ble",
            "events\n",
            "fact`orders",
            "fact orders",
            "fact-orders",
            "fact'orders",
        ],
    )
    def test_hostile_identifier_edge_set_raises(
        self, hostile: str, tmp_path: Path
    ) -> None:
        with pytest.raises(SqlError, match="not allowed"):
            _render_ident(tmp_path, hostile)

    def test_non_string_identifier_raises(self, tmp_path: Path) -> None:
        with pytest.raises(SqlError, match="must be a string"):
            _render_ident(tmp_path, 123)

    def test_undefined_through_ident_raises_with_cause(self, tmp_path: Path) -> None:
        (tmp_path / "t.sql.j2").write_text("FROM {{ table | ident }}", encoding="utf-8")

        with pytest.raises(SqlError) as exc_info:
            render_template("t", DbType.SQLITE, search_paths=[tmp_path])

        assert isinstance(exc_info.value.__cause__, UndefinedError)
