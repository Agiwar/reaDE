"""Tests for ConfigLoaderFactory."""

from pathlib import Path

import pytest

from reade.config import ConfigLoaderFactory
from reade.core.enums import FileType
from reade.core.errors import ConfigError


class TestConfigLoaderFactory:
    @pytest.mark.parametrize("file_type", [FileType.YAML, FileType.YML])
    def test_get_loader_returns_working_yaml_loader(
        self, file_type: FileType, tmp_path: Path
    ) -> None:
        file_path = tmp_path / f"config{file_type.value}"
        file_path.write_text("key: value\n")

        loader = ConfigLoaderFactory.get_loader(file_type)

        assert loader.load(file_path) == {"key": "value"}

    def test_get_loader_unregistered_type_raises_config_error(self) -> None:
        with pytest.raises(ConfigError, match="No loader registered"):
            ConfigLoaderFactory.get_loader(FileType.JSON)
