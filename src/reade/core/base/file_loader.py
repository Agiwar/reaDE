"""Base file loader with path resolution and content parsing."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class BaseFileLoader(ABC):
    """Abstract base for loading configuration files.

    Provides path resolution and file reading. Subclasses implement
    format-specific parsing via `_parse_content`.

    Attributes:
        base_path: Base directory for resolving relative paths.
    """

    def __init__(self, base_path: Path | None = None) -> None:
        """Initialize loader with optional base path.

        Args:
            base_path: Base directory for file resolution.
                Defaults to 'configurations/local'.
        """
        self.base_path = base_path or Path("configurations/local")

    def load(self, path: Path) -> dict[str, Any]:
        """Load and parse a configuration file.

        Args:
            path: Path to the configuration file. Absolute paths are
                used directly; relative paths resolve against base_path.

        Returns:
            Parsed configuration as a dictionary.
        """
        resolved_path = path if path.is_absolute() else self.base_path / path
        return self._parse_content(resolved_path.read_text(encoding="utf-8"))

    @abstractmethod
    def _parse_content(self, content: str) -> dict[str, Any]:
        """Parse file content into a dictionary.

        Args:
            content: Raw file content as string.

        Returns:
            Parsed configuration as a dictionary.
        """
        ...
