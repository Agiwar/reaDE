"""JSON config loader."""

import json
from typing import Any, cast

from reade.core.base.file_loader import BaseFileLoader


class JsonFileLoader(BaseFileLoader):
    """JSON configuration file loader.

    Inherits from BaseFileLoader to handle file reading and path resolution.
    Implements JSON-specific parsing.
    """

    def _parse_content(self, content: str) -> dict[str, Any]:
        """Parse JSON content into a dictionary.

        Args:
            content: Raw JSON file content as string.

        Returns:
            Parsed configuration as a dictionary. Empty dict if content is empty.
        """
        return cast(dict[str, Any], json.loads(content)) if content.strip() else {}
