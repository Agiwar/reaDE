"""JSON configuration loader."""

import json
from typing import Any, ClassVar

from reade.core.base.file_loader import FileLoaderBase
from reade.core.enums.file_type import FileType


class JsonLoader(FileLoaderBase):
    """Loads JSON configuration files (``.json``).

    Format-specific parsing only; reading, suffix validation, and error
    mapping live in ``FileLoaderBase``.
    """

    file_types: ClassVar[frozenset[FileType]] = frozenset({FileType.JSON})

    def _parse_content(self, content: str) -> dict[str, Any]:
        """Parse JSON content into a dictionary.

        Args:
            content: Raw JSON content.

        Returns:
            Parsed configuration as a dictionary.

        Raises:
            TypeError: If the document is not an object. Wrapped into
                ``ConfigError`` by ``FileLoaderBase.load``, as are the
                parser's own errors (``json.JSONDecodeError``).
        """
        data = json.loads(content)
        if not isinstance(data, dict):
            raise TypeError("JSON config must be an object, not an array or scalar")
        return data
