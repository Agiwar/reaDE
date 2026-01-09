"""Tests for YamlFileLoader."""

from pathlib import Path

import pytest
import yaml

from reade.config.loaders import YamlFileLoader


class TestYamlFileLoader:
    """Tests for YamlFileLoader.load() behavior."""

    def test_load_valid_yaml(self, valid_yaml_file: Path) -> None:
        """Load valid YAML returns parsed dict."""
        loader = YamlFileLoader(base_path=valid_yaml_file.parent)
        result = loader.load(Path(valid_yaml_file.name))

        assert result == {"database": {"host": "localhost", "port": 5432}}

    def test_load_empty_yaml(self, empty_yaml_file: Path) -> None:
        """Load empty YAML returns empty dict."""
        loader = YamlFileLoader(base_path=empty_yaml_file.parent)
        result = loader.load(Path(empty_yaml_file.name))

        assert result == {}

    def test_load_with_absolute_path(self, valid_yaml_file: Path) -> None:
        """Absolute path is used directly, ignoring base_path."""
        loader = YamlFileLoader(base_path=Path("/nonexistent"))
        result = loader.load(valid_yaml_file)  # absolute path

        assert result == {"database": {"host": "localhost", "port": 5432}}

    def test_load_with_relative_path(self, tmp_config_dir: Path) -> None:
        """Relative path resolves against base_path."""
        subdir = tmp_config_dir / "subdir"
        subdir.mkdir()
        config_file = subdir / "config.yaml"
        config_file.write_text("key: value\n")

        loader = YamlFileLoader(base_path=tmp_config_dir)
        result = loader.load(Path("subdir/config.yaml"))

        assert result == {"key": "value"}

    def test_load_file_not_found(self, tmp_config_dir: Path) -> None:
        """Missing file raises FileNotFoundError."""
        loader = YamlFileLoader(base_path=tmp_config_dir)

        with pytest.raises(FileNotFoundError):
            loader.load(Path("nonexistent.yaml"))

    def test_load_invalid_yaml(self, invalid_yaml_file: Path) -> None:
        """Invalid YAML raises yaml.YAMLError."""
        loader = YamlFileLoader(base_path=invalid_yaml_file.parent)

        with pytest.raises(yaml.YAMLError):
            loader.load(Path(invalid_yaml_file.name))

    def test_load_non_mapping_yaml_raises_type_error(
        self,
        tmp_config_dir: Path,
    ) -> None:
        """YAML list or scalar raises TypeError."""
        list_file = tmp_config_dir / "list.yaml"
        list_file.write_text("- item1\n- item2\n")

        loader = YamlFileLoader(base_path=tmp_config_dir)

        with pytest.raises(TypeError, match="must be a mapping"):
            loader.load(Path("list.yaml"))
