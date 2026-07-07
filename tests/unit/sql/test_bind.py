"""Tests for the bind filter: key policy, value handling, render guards."""

import datetime
from pathlib import Path
from typing import Any

import pytest
from jinja2 import UndefinedError

from reade.core.enums import DbType
from reade.core.errors import SqlError
from reade.sql import RenderedQuery, render_template


def _render(
    tmp_path: Path,
    content: str,
    context: dict[str, Any],
    dialect: DbType = DbType.SQLITE,
) -> RenderedQuery:
    (tmp_path / "t.sql.j2").write_text(content, encoding="utf-8")
    return render_template("t", dialect, context, search_paths=[tmp_path])


class TestBindKeys:
    def test_auto_keys_number_in_evaluation_order(self, tmp_path: Path) -> None:
        rendered = _render(tmp_path, "{{ a | bind }} {{ b | bind }}", {"a": 1, "b": 2})

        assert rendered.sql == ":p0 :p1"
        assert rendered.params == {"p0": 1, "p1": 2}

    @pytest.mark.parametrize(
        ("dialect", "expected_sql"),
        [
            (DbType.SQLITE, ":p0"),
            (DbType.MYSQL, "%(p0)s"),
            (DbType.POSTGRESQL, "%(p0)s"),
        ],
    )
    def test_placeholder_style_follows_dialect(
        self, dialect: DbType, expected_sql: str, tmp_path: Path
    ) -> None:
        rendered = _render(tmp_path, "{{ v | bind }}", {"v": 1}, dialect)

        assert rendered.sql == expected_sql

    def test_auto_binds_reuse_the_key_of_an_equal_value(self, tmp_path: Path) -> None:
        rendered = _render(tmp_path, "{{ a | bind }} {{ b | bind }}", {"a": 5, "b": 5})

        assert rendered.sql == ":p0 :p0"
        assert rendered.params == {"p0": 5}

    def test_equal_values_of_different_types_stay_distinct(
        self, tmp_path: Path
    ) -> None:
        rendered = _render(
            tmp_path, "{{ a | bind }} {{ b | bind }}", {"a": 1, "b": True}
        )

        assert rendered.params == {"p0": 1, "p1": True}

    def test_explicit_name_is_honored(self, tmp_path: Path) -> None:
        rendered = _render(tmp_path, '{{ v | bind("since") }}', {"v": "2026-01-01"})

        assert rendered.sql == ":since"
        assert rendered.params == {"since": "2026-01-01"}

    def test_explicit_rebind_with_equal_value_reuses_key(self, tmp_path: Path) -> None:
        rendered = _render(
            tmp_path, '{{ v | bind("day") }} {{ v | bind("day") }}', {"v": 7}
        )

        assert rendered.sql == ":day :day"
        assert rendered.params == {"day": 7}

    def test_explicit_rebind_with_different_value_gets_suffix(
        self, tmp_path: Path
    ) -> None:
        rendered = _render(
            tmp_path,
            '{{ a | bind("day") }} {{ b | bind("day") }}',
            {"a": 1, "b": 2},
        )

        assert rendered.sql == ":day :day_1"
        assert rendered.params == {"day": 1, "day_1": 2}

    def test_auto_key_skips_explicitly_taken_names(self, tmp_path: Path) -> None:
        rendered = _render(
            tmp_path, '{{ a | bind("p0") }} {{ b | bind }}', {"a": 1, "b": 2}
        )

        assert rendered.sql == ":p0 :p1"
        assert rendered.params == {"p0": 1, "p1": 2}

    @pytest.mark.parametrize("bad_name", ["p;q", "p0\n", "", "0abc", 123])
    def test_invalid_bind_name_raises(self, bad_name: object, tmp_path: Path) -> None:
        with pytest.raises(SqlError, match="Invalid bind name"):
            _render(tmp_path, "{{ v | bind(bad) }}", {"v": 1, "bad": bad_name})


class TestBindValues:
    def test_collection_value_raises(self, tmp_path: Path) -> None:
        with pytest.raises(SqlError, match="collection"):
            _render(tmp_path, "{{ v | bind }}", {"v": [1, 2]})

    def test_value_types_are_preserved(self, tmp_path: Path) -> None:
        context: dict[str, Any] = {
            "i": 42,
            "n": None,
            "b": b"x",
            "d": datetime.date(2026, 1, 1),
        }

        rendered = _render(
            tmp_path,
            "{{ i | bind }} {{ n | bind }} {{ b | bind }} {{ d | bind }}",
            context,
        )

        assert rendered.params == {
            "p0": 42,
            "p1": None,
            "p2": b"x",
            "p3": datetime.date(2026, 1, 1),
        }
        assert type(rendered.params["p0"]) is int
        assert type(rendered.params["p3"]) is datetime.date

    def test_undefined_through_bind_raises_with_cause(self, tmp_path: Path) -> None:
        with pytest.raises(SqlError) as exc_info:
            _render(tmp_path, "{{ missing | bind }}", {})

        assert isinstance(exc_info.value.__cause__, UndefinedError)


class TestRenderGuards:
    def test_bind_result_transformed_by_later_filter_raises(
        self, tmp_path: Path
    ) -> None:
        with pytest.raises(SqlError, match="no placeholder"):
            _render(tmp_path, "{{ v | bind | upper }}", {"v": 1})

    def test_orphaned_bind_raises(self, tmp_path: Path) -> None:
        with pytest.raises(SqlError, match="no placeholder"):
            _render(tmp_path, "{% set x = v | bind %}SELECT 1", {"v": 1})

    @pytest.mark.parametrize("dialect", [DbType.MYSQL, DbType.POSTGRESQL])
    def test_stray_percent_with_params_raises_for_pyformat(
        self, dialect: DbType, tmp_path: Path
    ) -> None:
        with pytest.raises(SqlError, match="'%%'"):
            _render(
                tmp_path,
                "SELECT {{ v | bind }} WHERE note LIKE '%x'",
                {"v": 1},
                dialect,
            )

    def test_escaped_percent_with_params_is_accepted(self, tmp_path: Path) -> None:
        rendered = _render(
            tmp_path,
            "SELECT {{ v | bind }} WHERE note LIKE '%%x'",
            {"v": 1},
            DbType.POSTGRESQL,
        )

        assert rendered.sql == "SELECT %(p0)s WHERE note LIKE '%%x'"

    def test_stray_percent_without_params_is_allowed(self, tmp_path: Path) -> None:
        rendered = _render(tmp_path, "SELECT '100%'", {}, DbType.POSTGRESQL)

        assert rendered.sql == "SELECT '100%'"
        assert rendered.params == {}

    def test_stray_percent_is_allowed_for_sqlite(self, tmp_path: Path) -> None:
        rendered = _render(
            tmp_path, "SELECT {{ v | bind }} WHERE note LIKE '%x'", {"v": 1}
        )

        assert rendered.sql == "SELECT :p0 WHERE note LIKE '%x'"
