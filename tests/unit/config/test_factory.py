"""Tests for ConfigLoaderFactory."""

from pathlib import Path

import pytest

from reade.config import ConfigLoaderFactory
from reade.core.enums import FileType
from reade.core.errors import ConfigError


class TestConfigLoaderFactory:
    @pytest.mark.parametrize(
        ("file_type", "content"),
        [
            (FileType.YAML, "key: value\n"),
            (FileType.YML, "key: value\n"),
            (FileType.JSON, '{"key": "value"}'),
        ],
    )
    def test_get_loader_returns_working_loader(
        self, file_type: FileType, content: str, tmp_path: Path
    ) -> None:
        file_path = tmp_path / f"config{file_type.value}"
        file_path.write_text(content)

        loader = ConfigLoaderFactory.get_loader(file_type)

        assert loader.load(file_path) == {"key": "value"}

    def test_get_loader_unregistered_type_raises_config_error(self) -> None:
        # CSV is the canonical unregistered type: it stays in the frozen
        # enum but never registers here (CSV is data, not config).
        with pytest.raises(ConfigError, match="No loader registered"):
            ConfigLoaderFactory.get_loader(FileType.CSV)
