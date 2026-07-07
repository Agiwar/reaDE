"""Tests for render_template."""

import sqlite3
from pathlib import Path

import pytest
from jinja2 import TemplateSyntaxError, UndefinedError

from reade.core.enums import DbType
from reade.core.errors import SqlError
from reade.sql import RenderedQuery, render_template

HOSTILE_VALUE = "1; DROP TABLE fact_orders;--"


def _write(tmp_path: Path, name: str, content: str) -> Path:
    (tmp_path / f"{name}.sql.j2").write_text(content, encoding="utf-8")
    return tmp_path


class TestRenderTemplate:
    def test_renders_row_count_template(self) -> None:
        rendered = render_template("row_count", DbType.SQLITE, {"table": "events"})

        assert isinstance(rendered, RenderedQuery)
        assert "SELECT COUNT(*) AS row_count" in rendered.sql
        assert 'FROM "events"' in rendered.sql
        assert rendered.params == {}

    @pytest.mark.parametrize(
        ("dialect", "expected_from"),
        [
            (DbType.SQLITE, 'FROM "events"'),
            (DbType.MYSQL, "FROM `events`"),
            (DbType.POSTGRESQL, 'FROM "events"'),
        ],
    )
    def test_row_count_quotes_the_table_for_every_dialect(
        self, dialect: DbType, expected_from: str
    ) -> None:
        rendered = render_template("row_count", dialect, {"table": "events"})

        assert expected_from in rendered.sql
        assert rendered.params == {}

    def test_unknown_template_raises_sql_error(self) -> None:
        with pytest.raises(SqlError, match="no_such_template"):
            render_template("no_such_template", DbType.SQLITE)

    def test_unknown_template_error_names_resolved_filename(self) -> None:
        with pytest.raises(SqlError, match=r"missing\.sql\.j2"):
            render_template("missing", DbType.SQLITE)

    def test_missing_context_variable_raises_sql_error_with_cause(self) -> None:
        with pytest.raises(SqlError) as exc_info:
            render_template("row_count", DbType.SQLITE)

        assert isinstance(exc_info.value.__cause__, UndefinedError)

    def test_unparsable_template_raises_sql_error_with_cause(
        self, tmp_path: Path
    ) -> None:
        _write(tmp_path, "broken", "SELECT {{ v")

        with pytest.raises(SqlError, match="Failed to load") as exc_info:
            render_template("broken", DbType.SQLITE, search_paths=[tmp_path])

        assert isinstance(exc_info.value.__cause__, TemplateSyntaxError)

    def test_caller_template_found_via_search_paths(self, tmp_path: Path) -> None:
        _write(tmp_path, "greet", "SELECT {{ v | bind }}")

        rendered = render_template(
            "greet", DbType.SQLITE, {"v": "hello"}, search_paths=[tmp_path]
        )

        assert rendered.sql == "SELECT :p0"
        assert rendered.params == {"p0": "hello"}

    def test_context_variable_named_dialect_renders(self, tmp_path: Path) -> None:
        _write(tmp_path, "probe", "SELECT {{ dialect | bind }}")

        rendered = render_template(
            "probe", DbType.SQLITE, {"dialect": "x"}, search_paths=[tmp_path]
        )

        assert rendered.params == {"p0": "x"}

    def test_postgres_type_cast_passes_through_untouched(self, tmp_path: Path) -> None:
        _write(tmp_path, "cast", "SELECT {{ v | bind }}::timestamp")

        rendered = render_template(
            "cast", DbType.POSTGRESQL, {"v": "2026-07-07"}, search_paths=[tmp_path]
        )

        assert rendered.sql == "SELECT %(p0)s::timestamp"

    def test_consecutive_renders_are_independent(self, tmp_path: Path) -> None:
        _write(tmp_path, "one", "SELECT {{ v | bind }}")

        first = render_template("one", DbType.SQLITE, {"v": 1}, search_paths=[tmp_path])
        second = render_template(
            "one", DbType.SQLITE, {"v": 2}, search_paths=[tmp_path]
        )

        assert first.params == {"p0": 1}
        assert second.params == {"p0": 2}
        assert first.params is not second.params

    def test_included_template_binds_accumulate(self, tmp_path: Path) -> None:
        _write(tmp_path, "child", "b = {{ b | bind }}")
        _write(
            tmp_path,
            "parent",
            'a = {{ a | bind }} AND {% include "child.sql.j2" %}',
        )

        rendered = render_template(
            "parent", DbType.SQLITE, {"a": 1, "b": 2}, search_paths=[tmp_path]
        )

        assert rendered.sql == "a = :p0 AND b = :p1"
        assert rendered.params == {"p0": 1, "p1": 2}


class TestInjectionSafety:
    @pytest.mark.parametrize("dialect", list(DbType))
    def test_hostile_value_lands_in_params_never_in_sql(
        self, dialect: DbType, tmp_path: Path
    ) -> None:
        _write(tmp_path, "notes", "SELECT * FROM notes WHERE note = {{ note | bind }}")

        rendered = render_template(
            "notes", dialect, {"note": HOSTILE_VALUE}, search_paths=[tmp_path]
        )

        assert rendered.params == {"p0": HOSTILE_VALUE}
        assert HOSTILE_VALUE not in rendered.sql
        assert "DROP TABLE" not in rendered.sql

    def test_hostile_value_round_trips_as_data_on_sqlite(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "insert_note",
            "INSERT INTO notes (body) VALUES ({{ body | bind }})",
        )
        connection = sqlite3.connect(":memory:")
        connection.execute("CREATE TABLE fact_orders (id INTEGER)")
        connection.execute("CREATE TABLE notes (body TEXT)")

        rendered = render_template(
            "insert_note",
            DbType.SQLITE,
            {"body": HOSTILE_VALUE},
            search_paths=[tmp_path],
        )
        connection.execute(rendered.sql, rendered.params)

        stored = connection.execute("SELECT body FROM notes").fetchall()
        surviving = connection.execute(
            "SELECT name FROM sqlite_master WHERE name = 'fact_orders'"
        ).fetchall()
        assert stored == [(HOSTILE_VALUE,)]
        assert surviving == [("fact_orders",)]
