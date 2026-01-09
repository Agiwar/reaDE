"""Configuration utility functions."""

from pathlib import Path
from typing import Any

from reade.config.factory import ConfigLoaderFactory
from reade.core.enums.file_type import FileType


def get_config_content(
    file_name: str,
    base_path: Path | None = None,
) -> dict[str, Any]:
    """Load configuration content from a file.

    Auto-detects file type from extension and returns parsed content.
    Path resolution is handled by the loader.

    Args:
        file_name: Name of the config file (e.g., "db.yaml").
            Resolved against base_path by the loader.
        base_path: Base directory for resolving the file path.
            If None, loader uses its default ("configuration/local").

    Returns:
        Parsed configuration as a dictionary.

    Raises:
        ValueError: If file extension is unsupported.

    Example:
        >>> config = get_config_content("db.yaml")
        >>> config = get_config_content("app.yaml", base_path=Path("config/prod"))
    """
    path = Path(file_name)
    file_type = FileType(path.suffix.lower())
    loader = ConfigLoaderFactory.get_loader(file_type, base_path)
    return loader.load(path)
