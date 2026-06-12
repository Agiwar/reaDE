"""Tests for render_template."""

import pytest
from jinja2 import UndefinedError

from reade.core.errors import SqlError
from reade.sql import render_template


class TestRenderTemplate:
    def test_renders_row_count_template(self) -> None:
        sql = render_template("row_count", table="events")

        assert "SELECT COUNT(*) AS row_count" in sql
        assert "FROM events" in sql

    def test_unknown_template_raises_sql_error(self) -> None:
        with pytest.raises(SqlError, match="no_such_template"):
            render_template("no_such_template")

    def test_missing_parameter_raises_sql_error_with_cause(self) -> None:
        with pytest.raises(SqlError) as exc_info:
            render_template("row_count")

        assert isinstance(exc_info.value.__cause__, UndefinedError)
