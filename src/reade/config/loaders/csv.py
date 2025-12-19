"""CSV config loader."""

import csv
import io
from typing import Any

from reade.core.base.file_loader import BaseFileLoader


class CsvFileLoader(BaseFileLoader):
    """CSV configuration file loader.

    Parses CSV as key-value pairs (first column = key, second column = value).
    Inherits from BaseFileLoader to handle file reading and path resolution.
    """

    def _parse_content(self, content: str) -> dict[str, Any]:
        """Parse CSV content into a dictionary.

        Args:
            content: Raw CSV file content as string.

        Returns:
            Parsed configuration as a dictionary with first column as keys
            and second column as values. Empty dict if content is empty.
        """
        reader = csv.reader(io.StringIO(content))
        return {row[0]: row[1] if len(row) > 1 else None for row in reader if row}
