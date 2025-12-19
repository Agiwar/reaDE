"""Tests for JsonFileLoader."""

import json
from pathlib import Path

import pytest

from reade.config.loaders import JsonFileLoader


class TestJsonFileLoader:
    """Tests for JsonFileLoader.load() behavior."""

    def test_load_valid_json(self, valid_json_file: Path) -> None:
        """Load valid JSON returns parsed dict."""
        loader = JsonFileLoader(base_path=valid_json_file.parent)
        result = loader.load(Path(valid_json_file.name))

        assert result == {"database": {"host": "localhost", "port": 5432}}

    def test_load_empty_json(self, empty_json_file: Path) -> None:
        """Load empty JSON returns empty dict."""
        loader = JsonFileLoader(base_path=empty_json_file.parent)
        result = loader.load(Path(empty_json_file.name))

        assert result == {}

    def test_load_with_absolute_path(self, valid_json_file: Path) -> None:
        """Absolute path is used directly."""
        loader = JsonFileLoader(base_path=Path("/nonexistent"))
        result = loader.load(valid_json_file)  # absolute path

        assert result == {"database": {"host": "localhost", "port": 5432}}

    def test_load_file_not_found(self, tmp_config_dir: Path) -> None:
        """Missing file raises FileNotFoundError."""
        loader = JsonFileLoader(base_path=tmp_config_dir)

        with pytest.raises(FileNotFoundError):
            loader.load(Path("nonexistent.json"))

    def test_load_invalid_json(self, invalid_json_file: Path) -> None:
        """Invalid JSON raises json.JSONDecodeError."""
        loader = JsonFileLoader(base_path=invalid_json_file.parent)

        with pytest.raises(json.JSONDecodeError):
            loader.load(Path(invalid_json_file.name))
