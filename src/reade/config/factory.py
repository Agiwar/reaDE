"""Configuration factory functions."""

from pathlib import Path
from typing import ClassVar

from reade.config.loaders.csv import CsvFileLoader
from reade.config.loaders.json import JsonFileLoader
from reade.config.loaders.yaml import YamlFileLoader
from reade.core.base.file_loader import FileLoaderBase
from reade.core.enums.file_type import FileType
from reade.core.interfaces.config_loader import ConfigLoader


class ConfigLoaderFactory:
    """Factory for creating configuration file loaders."""

    _loaders: ClassVar[dict[FileType, type[FileLoaderBase]]] = {
        FileType.CSV: CsvFileLoader,
        FileType.JSON: JsonFileLoader,
        FileType.YAML: YamlFileLoader,
        FileType.YML: YamlFileLoader,
    }

    @classmethod
    def get_loader(
        cls,
        file_type: FileType,
        base_path: Path | None = None,
    ) -> ConfigLoader:
        """Get the appropriate config file loader based on file type.

        Args:
            file_type: The type of the config file (FileType.YAML, etc.).
            base_path: Base directory for resolving relative paths.
                Passed to loader constructor. If None, loader uses its default.

        Returns:
            An instance of the corresponding config file loader.

        Raises:
            ValueError: If the file type is unsupported.
        """
        if file_type not in cls._loaders:
            raise ValueError(f"Unsupported file type: {file_type}")
        return cls._loaders[file_type](base_path)
