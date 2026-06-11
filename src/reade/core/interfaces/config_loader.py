"""Config loader protocol for loading configuration files."""

from pathlib import Path
from typing import Any, Protocol


class ConfigLoader(Protocol):
    """Protocol for loading configuration files into dictionaries.

    Implementations handle specific formats (YAML, JSON, CSV).
    The loader is format-aware but content-agnostic.
    """

    def load(self, path: Path) -> dict[str, Any]:
        """Load configuration file and return parsed content.

        Args:
            path: Path to the configuration file.

        Returns:
            Parsed configuration as a dictionary.

        Raises:
            FileNotFoundError: If the file does not exist; passed through
                unchanged.
            ConfigError: If the file content cannot be parsed. The original
                parser exception is attached as the cause
                (``raise ... from``).
        """
        ...
