"""YAML configuration loader."""

from typing import Any, ClassVar

import yaml

from reade.core.base.file_loader import FileLoaderBase
from reade.core.enums.file_type import FileType


class YamlLoader(FileLoaderBase):
    """Loads YAML configuration files (``.yaml`` / ``.yml``).

    Format-specific parsing only; reading, suffix validation, and error
    mapping live in ``FileLoaderBase``.
    """

    file_types: ClassVar[frozenset[FileType]] = frozenset({FileType.YAML, FileType.YML})

    def _parse_content(self, content: str) -> dict[str, Any]:
        """Parse YAML content into a dictionary.

        Args:
            content: Raw YAML content.

        Returns:
            Parsed configuration as a dictionary; an empty document
            parses to an empty dictionary.

        Raises:
            TypeError: If the document is not a mapping. Wrapped into
                ``ConfigError`` by ``FileLoaderBase.load``, as are the
                parser's own errors (``yaml.YAMLError``).
        """
        data = yaml.safe_load(content)
        if data is None:
            return {}
        if not isinstance(data, dict):
            raise TypeError("YAML config must be a mapping, not a sequence or scalar")
        return data
