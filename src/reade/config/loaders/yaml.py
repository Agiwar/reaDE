"""YAML config loader."""

from typing import Any

import yaml

from reade.core.base.file_loader import FileLoaderBase


class YamlFileLoader(FileLoaderBase):
    """YAML configuration file loader.

    Inherits from FileLoaderBase to handle file reading and path
    resolution. Implements YAML-specific parsing.
    """

    def _parse_content(self, content: str) -> dict[str, Any]:
        """Parse YAML content into a dictionary.

        Args:
            content: Raw YAML file content as string.

        Returns:
            Parsed configuration as a dictionary.

        Raises:
            TypeError: If YAML content is not a mapping (e.g., list or scalar).
        """
        if (result := yaml.safe_load(content)) is None:
            return {}
        if not isinstance(result, dict):
            raise TypeError("YAML content must be a mapping, not sequence or scalar")
        return result
