"""YAML config loader."""

from typing import Any

import yaml

from reade.core.base.file_loader import BaseFileLoader


class YamlFileLoader(BaseFileLoader):
    """YAML configuration file loader.

    Inherits from BaseFileLoader to handle file reading and path
    resolution. Implements YAML-specific parsing.
    """

    def _parse_content(self, content: str) -> dict[str, Any]:
        """Parse YAML content into a dictionary.

        Args:
            content: Raw YAML file content as string.

        Returns:
            Parsed configuration as a dictionary.
        """
        return yaml.safe_load(content) or {}
