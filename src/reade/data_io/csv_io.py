"""CSV reading and writing for tabular data files.

CSV is data, not config (the Sprint 1.1 relocation decision): these
readers live in data_io and feed the validation layer, which owns type
coercion. Values cross this boundary as raw strings.
"""

import csv
from collections.abc import Iterable, Iterator, Mapping
from pathlib import Path
from typing import Any, TextIO

from reade.core.errors.data_io import DataIoError


def read_csv(path: str | Path) -> Iterator[dict[str, str]]:
    """Read a CSV file and yield one dict per row, keyed by header.

    Streaming by design: rows are yielded as they are read, so files
    larger than memory can be processed — ``list(read_csv(path))``
    materializes. Values stay raw strings; type coercion is the
    validation layer's job, never the reader's.

    The file is opened and the header validated eagerly at the call, so
    a missing file or a headerless file fails loud immediately. A row
    with the wrong number of fields raises at the offending row during
    iteration, after earlier rows have already been yielded — a reader
    that silently pads or truncates would misreport the data. Entirely
    blank lines are skipped (the ``csv.DictReader`` precedent: a blank
    line is not a row). Closing a partially consumed iterator releases
    the file; an iterator that is never advanced holds the file open
    until it is garbage-collected (closing an unstarted generator
    discards its frame without running the cleanup).

    Args:
        path: Path to the CSV file. Read as UTF-8, comma-delimited,
            with the first row as the header.

    Returns:
        An iterator of rows in file order, each a dict mapping header
        names to raw string values.

    Raises:
        DataIoError: If the file has no header row, a duplicate header
            name (dict rows cannot represent one honestly), a row whose
            field count differs from the header's (raised during
            iteration), or content the csv parser rejects — the parser
            error is attached as the cause.
        OSError: If the file cannot be opened or read; passed through
            unchanged (including ``FileNotFoundError``).

    Stability: stable.
    """
    # The returned iterator owns the handle: _generate_rows wraps it in
    # a with-block, so it closes on exhaustion, error, or generator
    # close. A with-block HERE would close it before iteration starts.
    file = Path(path).open(encoding="utf-8", newline="")  # noqa: SIM115
    try:
        reader = csv.reader(file)
        header = _read_header(reader, str(path))
    except BaseException:
        file.close()
        raise
    return _generate_rows(file, reader, header, str(path))


def _read_header(reader: Iterator[list[str]], path: str) -> list[str]:
    """Read and validate the header row.

    Args:
        reader: A csv reader positioned at the start of the file.
        path: The file path, for error messages.

    Returns:
        The validated header names.

    Raises:
        DataIoError: If the file has no header row, the header cannot
            be parsed, or a header name repeats.
    """
    try:
        header = next(reader)
    except StopIteration:
        raise DataIoError(f"CSV file {path!r} has no header row") from None
    except csv.Error as e:
        raise DataIoError(f"Failed to parse CSV file {path!r}") from e
    if len(set(header)) != len(header):
        raise DataIoError(
            f"CSV file {path!r} has duplicate header names; rows cannot "
            "be represented as dicts"
        )
    return header


def _generate_rows(
    file: TextIO,
    reader: Iterator[list[str]],
    header: list[str],
    path: str,
) -> Iterator[dict[str, str]]:
    """Yield validated dict rows, owning the open file until exhaustion.

    Args:
        file: The open file backing ``reader``; closed on exhaustion,
            error, or generator close.
        reader: The csv reader positioned after the header row.
        header: The validated header names.
        path: The file path, for error messages.

    Yields:
        One dict per non-blank row, keyed by ``header``.

    Raises:
        DataIoError: On a ragged row or a parser failure.
    """
    with file:
        try:
            for row_number, row in enumerate(reader, start=2):
                if not row:  # blank line, not a row
                    continue
                if len(row) != len(header):
                    raise DataIoError(
                        f"CSV file {path!r} row {row_number} has "
                        f"{len(row)} fields, expected {len(header)}"
                    )
                yield dict(zip(header, row, strict=True))
        except csv.Error as e:
            raise DataIoError(f"Failed to parse CSV file {path!r}") from e


def write_csv(path: str | Path, rows: Iterable[Mapping[str, Any]]) -> None:
    """Write rows of dicts to a CSV file, header from the first row.

    The header is the first row's keys in order. Every subsequent row
    must have exactly that key set — a row that differs raises rather
    than being padded or truncated, mirroring the reader's strictness.
    ``rows`` is consumed lazily, so a generator works; on a shape
    failure mid-write the file keeps the rows already written.

    Values are written with the csv module's string conversion; reading
    the file back with ``read_csv`` yields every value as a raw string.

    Args:
        path: Destination file path, written as UTF-8.
        rows: The rows to write, each a mapping of column name to
            value. Must yield at least one row — the header is derived
            from it.

    Raises:
        DataIoError: If ``rows`` is empty (no header is derivable), or
            a row's keys differ from the first row's.
        OSError: If the file cannot be created or written; passed
            through unchanged.

    Stability: stable.
    """
    iterator = iter(rows)
    try:
        first = next(iterator)
    except StopIteration:
        raise DataIoError(
            f"Cannot write CSV file {str(path)!r}: no rows, so no header is derivable"
        ) from None
    fieldnames = list(first.keys())
    with Path(path).open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(first)
        for row_number, row in enumerate(iterator, start=3):
            if set(row.keys()) != set(fieldnames):
                raise DataIoError(
                    f"Cannot write CSV file {str(path)!r}: row {row_number} "
                    f"keys {sorted(row.keys())} differ from the header "
                    f"{sorted(fieldnames)}"
                )
            writer.writerow(row)
