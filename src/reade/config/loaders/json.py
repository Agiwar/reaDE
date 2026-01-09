"""JSON config loader."""

import json
from typing import Any

from reade.core.base.file_loader import FileLoaderBase


class JsonFileLoader(FileLoaderBase):
    """JSON configuration file loader.

    Inherits from FileLoaderBase to handle file reading and path resolution.
    Implements JSON-specific parsing.
    """

    def _parse_content(self, content: str) -> dict[str, Any]:
        """Parse JSON content into a dictionary.

        Args:
            content: Raw JSON file content as string.

        Returns:
            Parsed configuration as a dictionary. Empty dict if content is empty.
        """
        if not content.strip():
            return {}
        result = json.loads(content)
        if not isinstance(result, dict):
            raise TypeError("JSON content must be an object, not array or primitive")
        return result
