"""Tests for YamlLoader specifics beyond the ConfigLoader contract."""

from pathlib import Path

import pytest

from reade.config import YamlLoader
from reade.core.errors import ConfigError


class TestYamlLoader:
    def test_load_empty_yaml_returns_empty_dict(self, empty_yaml_file: Path) -> None:
        assert YamlLoader().load(empty_yaml_file) == {}

    def test_load_accepts_yml_suffix(self, tmp_path: Path) -> None:
        file_path = tmp_path / "config.yml"
        file_path.write_text("key: value\n")

        assert YamlLoader().load(file_path) == {"key": "value"}

    def test_non_mapping_yaml_raises_config_error_with_cause(
        self, tmp_path: Path
    ) -> None:
        file_path = tmp_path / "list.yaml"
        file_path.write_text("- item1\n- item2\n")

        with pytest.raises(ConfigError) as exc_info:
            YamlLoader().load(file_path)

        assert isinstance(exc_info.value.__cause__, TypeError)
