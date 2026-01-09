"""Tests for config utility functions."""

from pathlib import Path

import pytest

from reade.config.utils import get_config_content


class TestGetConfigContent:
    """Tests for get_config_content() behavior."""

    def test_load_yaml_file(self, valid_yaml_file: Path) -> None:
        """Load YAML file returns parsed dict."""
        result = get_config_content(
            valid_yaml_file.name,
            base_path=valid_yaml_file.parent,
        )

        assert result == {"database": {"host": "localhost", "port": 5432}}

    def test_load_json_file(self, valid_json_file: Path) -> None:
        """Load JSON file returns parsed dict."""
        result = get_config_content(
            valid_json_file.name,
            base_path=valid_json_file.parent,
        )

        assert result == {"database": {"host": "localhost", "port": 5432}}

    def test_load_csv_file(self, valid_csv_file: Path) -> None:
        """Load CSV file returns parsed dict."""
        result = get_config_content(
            valid_csv_file.name,
            base_path=valid_csv_file.parent,
        )

        assert result == {"host": "localhost", "port": "5432"}

    def test_load_with_custom_base_path(self, tmp_config_dir: Path) -> None:
        """Custom base_path resolves file correctly."""
        subdir = tmp_config_dir / "custom"
        subdir.mkdir()
        config_file = subdir / "app.yaml"
        config_file.write_text("env: production\n")

        result = get_config_content("app.yaml", base_path=subdir)

        assert result == {"env": "production"}

    def test_load_with_default_base_path(
        self,
        tmp_config_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Without base_path, uses loader's default."""
        # Create file in default location relative to cwd
        default_dir = tmp_config_dir / "configuration" / "local"
        default_dir.mkdir(parents=True)
        config_file = default_dir / "db.yaml"
        config_file.write_text("host: localhost\n")

        # Change cwd so default path resolves
        monkeypatch.chdir(tmp_config_dir)

        result = get_config_content("db.yaml")

        assert result == {"host": "localhost"}

    def test_invalid_extension_raises_value_error(
        self,
        tmp_config_dir: Path,
    ) -> None:
        """Unsupported file extension raises ValueError."""
        with pytest.raises(ValueError, match="not a valid FileType"):
            get_config_content("config.txt", base_path=tmp_config_dir)

    def test_load_yml_extension(self, tmp_config_dir: Path) -> None:
        """Load .yml file (alternative YAML extension)."""
        config_file = tmp_config_dir / "config.yml"
        config_file.write_text("key: value\n")

        result = get_config_content("config.yml", base_path=tmp_config_dir)

        assert result == {"key": "value"}
