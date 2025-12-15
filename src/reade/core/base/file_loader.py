"""Base file loader with path resolution and content parsing."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class BaseFileLoader(ABC):
    """Abstract base for loading configuration files.

    Provides path resolution and file reading. Subclasses implement
    format-specific parsing via `_parse_content`.

    Attributes:
        base_file: Base directory for resolving relative file names.
    """

    def __init__(self, base_path: Path | None = None) -> None:
        """Initialize loader with optional base path.

        Args:
            base_path: Base directory for file resolution.
                Defaults to 'configurations/local'.
        """
        self.base_file = base_path or Path("configurations/local")

    def load(self, path: Path) -> dict[str, Any]:
        """Load and parse a configuration file.

        Args:
            path: Path to the configuration file. Only the filename
                is used; directory is resolved from base_file.

        Returns:
            Parsed configuration as a dictionary.
        """
        path = self._resolve_path(path.name)
        content = path.read_text(encoding="utf-8")
        return self._parse_content(content)

    def _resolve_path(self, file_name: str) -> Path:
        """Resolve filename against base directory.

        Args:
            file_name: Name of the file to resolve.

        Returns:
            Full path to the file.
        """
        return self.base_file / file_name

    @abstractmethod
    def _parse_content(self, content: str) -> dict[str, Any]:
        """Parse file content into a dictionary.

        Args:
            content: Raw file content as string.

        Returns:
            Parsed configuration as a dictionary.
        """
        ...
