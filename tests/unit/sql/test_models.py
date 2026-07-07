"""Tests for RenderedQuery."""

from dataclasses import FrozenInstanceError

import pytest

from reade.sql import RenderedQuery


class TestRenderedQuery:
    def test_is_immutable(self) -> None:
        rendered = RenderedQuery(sql="SELECT 1", params={})

        with pytest.raises(FrozenInstanceError):
            rendered.sql = "SELECT 2"  # type: ignore[misc]

    def test_equality_compares_sql_and_params(self) -> None:
        rendered = RenderedQuery(sql="SELECT 1", params={"p0": 1})

        assert rendered == RenderedQuery(sql="SELECT 1", params={"p0": 1})
        assert rendered != RenderedQuery(sql="SELECT 1", params={"p0": 2})
        assert rendered != RenderedQuery(sql="SELECT 2", params={"p0": 1})

    def test_is_hashable_despite_mutable_params(self) -> None:
        first = RenderedQuery(sql="SELECT 1", params={"p0": 1})
        second = RenderedQuery(sql="SELECT 1", params={"p0": 1})

        assert hash(first) == hash(second)
