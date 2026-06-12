"""Base file loader implementing the shared loading template."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, ClassVar

from reade.core.enums.file_type import FileType
from reade.core.errors.base import ReadeError
from reade.core.errors.config import ConfigError


class FileLoaderBase(ABC):
    """Template-method base for configuration file loaders.

    Implements the shared loading pipeline — suffix guard, file read,
    error mapping — so subclasses only provide format-specific parsing
    via ``_parse_content``. Satisfies the ``ConfigLoader`` protocol.

    Attributes:
        file_types: The file types this loader handles. Subclasses must
            declare it. The suffix guard in ``load`` validates against
            this loader's own types only — never against all known
            types — so a loader can never silently parse a format it
            does not own. Factories derive their type-to-loader mapping
            from the same declaration.
    """

    file_types: ClassVar[frozenset[FileType]]

    def load(self, path: Path) -> dict[str, Any]:
        """Load a configuration file and return its parsed content.

        Args:
            path: Path to the configuration file.

        Returns:
            Parsed configuration as a dictionary.

        Raises:
            OSError: If the file cannot be read (including
                ``FileNotFoundError``); passed through unchanged.
            ConfigError: If this loader does not handle the file's
                format, or the content cannot be parsed. For parse
                failures the original parser exception is attached as
                the cause (``raise ... from``).
        """
        suffix = path.suffix.lower()
        if suffix not in {file_type.value for file_type in self.file_types}:
            raise ConfigError(f"{type(self).__name__} does not handle {suffix!r}")

        content = path.read_text(encoding="utf-8")
        try:
            return self._parse_content(content)
        except ReadeError:
            raise
        except Exception as e:
            raise ConfigError(f"Failed to parse {path}") from e

    @abstractmethod
    def _parse_content(self, content: str) -> dict[str, Any]:
        """Parse raw file content into a dictionary.

        Implementations are format-specific and must not perform error
        mapping: any exception raised here is wrapped into ``ConfigError``
        by ``load``.

        Args:
            content: Raw file content.

        Returns:
            Parsed configuration as a dictionary.
        """
