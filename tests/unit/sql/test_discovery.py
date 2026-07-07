"""Tests for the template discovery convention.

Discovery surface: the packaged templates directory plus caller-supplied
``search_paths``, nothing else. Packaged names always win; lookup is by
bare name with the fixed ``.sql.j2`` extension; environments are cached
per resolved search-path tuple with live reloading of edited files.
"""

import os
from pathlib import Path

import pytest

from reade.core.enums import DbType
from reade.core.errors import SqlError
from reade.sql import render_template
from reade.sql.render import _build_environment


class TestDiscoveryConvention:
    def test_packaged_template_wins_over_search_path_shadow(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "row_count.sql.j2").write_text(
            "SELECT 'shadowed'", encoding="utf-8"
        )

        rendered = render_template(
            "row_count", DbType.SQLITE, {"table": "events"}, search_paths=[tmp_path]
        )

        assert "shadowed" not in rendered.sql
        assert 'FROM "events"' in rendered.sql

    def test_path_traversal_in_template_name_is_blocked(self, tmp_path: Path) -> None:
        templates = tmp_path / "templates"
        templates.mkdir()
        (tmp_path / "secret.sql.j2").write_text("SELECT 'secret'", encoding="utf-8")

        with pytest.raises(SqlError, match="not found"):
            render_template("../secret", DbType.SQLITE, search_paths=[templates])

    def test_lookup_uses_only_the_sql_j2_extension(self, tmp_path: Path) -> None:
        (tmp_path / "probe.sql").write_text("SELECT 1", encoding="utf-8")
        (tmp_path / "probe.j2").write_text("SELECT 1", encoding="utf-8")

        with pytest.raises(SqlError, match=r"probe\.sql\.j2"):
            render_template("probe", DbType.SQLITE, search_paths=[tmp_path])

    def test_nonexistent_search_dir_is_tolerated(self, tmp_path: Path) -> None:
        missing = tmp_path / "does_not_exist"

        rendered = render_template(
            "row_count", DbType.SQLITE, {"table": "events"}, search_paths=[missing]
        )

        assert 'FROM "events"' in rendered.sql

    def test_environment_is_cached_per_search_path_tuple(self, tmp_path: Path) -> None:
        first = _build_environment((str(tmp_path),))
        second = _build_environment((str(tmp_path),))
        different = _build_environment(())

        assert first is second
        assert first is not different

    def test_edited_caller_template_is_picked_up_across_renders(
        self, tmp_path: Path
    ) -> None:
        template = tmp_path / "probe.sql.j2"
        template.write_text("SELECT 1", encoding="utf-8")
        rendered_before = render_template(
            "probe", DbType.SQLITE, search_paths=[tmp_path]
        )

        template.write_text("SELECT 2", encoding="utf-8")
        stat = template.stat()
        os.utime(template, (stat.st_atime, stat.st_mtime + 2))
        rendered_after = render_template(
            "probe", DbType.SQLITE, search_paths=[tmp_path]
        )

        assert rendered_before.sql == "SELECT 1"
        assert rendered_after.sql == "SELECT 2"
