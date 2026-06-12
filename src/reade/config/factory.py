"""Configuration loader factory."""

from typing import ClassVar

from reade.config.loaders.yaml import YamlLoader
from reade.core.base.file_loader import FileLoaderBase
from reade.core.enums.file_type import FileType
from reade.core.errors.config import ConfigError
from reade.core.interfaces.config_loader import ConfigLoader


class ConfigLoaderFactory:
    """Maps file types to configuration loader implementations.

    The only place a ``FileType`` is resolved to a concrete loader. The
    mapping is derived from each loader's own ``file_types`` declaration,
    sharing one source of truth with the suffix guard in
    ``FileLoaderBase.load``.
    """

    _loaders: ClassVar[dict[FileType, type[FileLoaderBase]]] = dict.fromkeys(
        YamlLoader.file_types, YamlLoader
    )

    @classmethod
    def get_loader(cls, file_type: FileType) -> ConfigLoader:
        """Return a loader instance for the given file type.

        Args:
            file_type: The configuration file type.

        Returns:
            A loader satisfying the ``ConfigLoader`` protocol.

        Raises:
            ConfigError: If no loader is registered for the file type.
                Only YAML is registered today; JSON and CSV follow.
        """
        try:
            loader_cls = cls._loaders[file_type]
        except KeyError as e:
            raise ConfigError(
                f"No loader registered for file type {file_type.value!r}"
            ) from e
        return loader_cls()
