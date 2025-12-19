"""Tests for CsvFileLoader."""

from pathlib import Path

import pytest

from reade.config.loaders import CsvFileLoader


class TestCsvFileLoader:
    """Tests for CsvFileLoader.load() behavior."""

    def test_load_valid_csv(self, valid_csv_file: Path) -> None:
        """Load valid CSV returns parsed dict."""
        loader = CsvFileLoader(base_path=valid_csv_file.parent)
        result = loader.load(Path(valid_csv_file.name))

        assert result == {"host": "localhost", "port": "5432"}

    def test_load_empty_csv(self, empty_csv_file: Path) -> None:
        """Load empty CSV returns empty dict."""
        loader = CsvFileLoader(base_path=empty_csv_file.parent)
        result = loader.load(Path(empty_csv_file.name))

        assert result == {}

    def test_load_keys_only(self, keys_only_csv_file: Path) -> None:
        """CSV with only keys returns None for values."""
        loader = CsvFileLoader(base_path=keys_only_csv_file.parent)
        result = loader.load(Path(keys_only_csv_file.name))

        assert result == {"host": None, "port": None}

    def test_load_extra_columns_ignored(self, extra_columns_csv_file: Path) -> None:
        """Extra columns beyond key-value are ignored."""
        loader = CsvFileLoader(base_path=extra_columns_csv_file.parent)
        result = loader.load(Path(extra_columns_csv_file.name))

        assert result == {"host": "localhost", "port": "5432"}

    def test_load_quoted_values(self, quoted_csv_file: Path) -> None:
        """Quoted values with commas are parsed correctly."""
        loader = CsvFileLoader(base_path=quoted_csv_file.parent)
        result = loader.load(Path(quoted_csv_file.name))

        assert result == {"message": "Hello, World", "path": "/usr/local/bin"}

    def test_load_with_absolute_path(self, valid_csv_file: Path) -> None:
        """Absolute path is used directly."""
        loader = CsvFileLoader(base_path=Path("/nonexistent"))
        result = loader.load(valid_csv_file)  # absolute path

        assert result == {"host": "localhost", "port": "5432"}

    def test_load_file_not_found(self, tmp_config_dir: Path) -> None:
        """Missing file raises FileNotFoundError."""
        loader = CsvFileLoader(base_path=tmp_config_dir)

        with pytest.raises(FileNotFoundError):
            loader.load(Path("nonexistent.csv"))
