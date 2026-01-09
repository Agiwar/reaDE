"""File type enumeration for supported file formats."""

from enum import StrEnum


class FileType(StrEnum):
    """Supported file formats for config and data I/O.

    Attributes:
        YAML: YAML config files (.yaml, .yml).
        JSON: JSON config/data files.
        CSV: CSV data files.
    """

    YAML = ".yaml"
    YML = ".yml"
    JSON = ".json"
    CSV = ".csv"
