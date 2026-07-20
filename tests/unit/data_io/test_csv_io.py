"""Tests for read_csv / write_csv.

The ruled contract (2.2 kickoff): functions, not classes; rows are
dicts keyed by header; values stay raw strings (coercion is the
validation layer's job); ragged rows raise; parse and shape failures
map to ``DataIoError``; ``OSError`` passes through unchanged. The
reader streams (the 2.2 results decision) — ``list()`` materializes.
"""

from collections.abc import Generator, Iterator
from pathlib import Path

import pytest

from reade.core.errors import DataIoError
from reade.data_io import read_csv, write_csv


@pytest.fixture
def events_csv(tmp_path: Path) -> Path:
    file_path = tmp_path / "events.csv"
    file_path.write_text(
        "event_name,event_count\nsignup,2\nlogin,1\n", encoding="utf-8"
    )
    return file_path


class TestReadCsv:
    def test_yields_dict_rows_keyed_by_header(self, events_csv: Path) -> None:
        rows = list(read_csv(events_csv))

        assert rows == [
            {"event_name": "signup", "event_count": "2"},
            {"event_name": "login", "event_count": "1"},
        ]

    def test_values_stay_raw_strings(self, events_csv: Path) -> None:
        rows = list(read_csv(events_csv))

        assert all(isinstance(value, str) for row in rows for value in row.values())

    def test_reader_streams_rather_than_materializing(self, events_csv: Path) -> None:
        result = read_csv(events_csv)

        assert isinstance(result, Iterator)
        assert next(result) == {"event_name": "signup", "event_count": "2"}
        # The public type is Iterator; narrowing to Generator lets the
        # test exercise close() — partial consumption must release the
        # file cleanly.
        assert isinstance(result, Generator)
        result.close()

    def test_header_only_file_yields_nothing(self, tmp_path: Path) -> None:
        file_path = tmp_path / "empty_data.csv"
        file_path.write_text("a,b\n", encoding="utf-8")

        assert list(read_csv(file_path)) == []

    def test_blank_lines_are_skipped(self, tmp_path: Path) -> None:
        # The csv.DictReader precedent: an entirely blank line is not a
        # row; a row with the wrong number of fields is (and raises).
        file_path = tmp_path / "blank_line.csv"
        file_path.write_text("a,b\n1,2\n\n3,4\n", encoding="utf-8")

        assert list(read_csv(file_path)) == [
            {"a": "1", "b": "2"},
            {"a": "3", "b": "4"},
        ]

    def test_missing_file_passes_file_not_found_through(self, tmp_path: Path) -> None:
        # The ruled error contract encoded: OSError passthrough, so the
        # exception must be FileNotFoundError itself, never DataIoError.
        with pytest.raises(FileNotFoundError):
            read_csv(tmp_path / "absent.csv")

    def test_empty_file_raises_data_io_error(self, tmp_path: Path) -> None:
        file_path = tmp_path / "empty.csv"
        file_path.write_text("", encoding="utf-8")

        with pytest.raises(DataIoError, match="no header row"):
            read_csv(file_path)

    def test_duplicate_header_names_raise(self, tmp_path: Path) -> None:
        file_path = tmp_path / "dupe.csv"
        file_path.write_text("a,a\n1,2\n", encoding="utf-8")

        with pytest.raises(DataIoError, match="duplicate header"):
            read_csv(file_path)

    def test_ragged_row_raises_at_the_offending_row(self, tmp_path: Path) -> None:
        # Mid-iteration error semantics: rows before the ragged one have
        # already been yielded when the error surfaces.
        file_path = tmp_path / "ragged.csv"
        file_path.write_text("a,b\n1,2\n3\n", encoding="utf-8")
        rows = read_csv(file_path)

        assert next(rows) == {"a": "1", "b": "2"}
        with pytest.raises(DataIoError, match="row 3"):
            next(rows)

    def test_too_many_fields_raise(self, tmp_path: Path) -> None:
        file_path = tmp_path / "wide.csv"
        file_path.write_text("a,b\n1,2,3\n", encoding="utf-8")

        with pytest.raises(DataIoError, match="expected 2"):
            list(read_csv(file_path))

    def test_parser_failure_wraps_csv_error_with_cause(self, tmp_path: Path) -> None:
        # A field beyond csv.field_size_limit() is the parser failure
        # the csv module still raises on under Python 3.12.
        file_path = tmp_path / "huge_field.csv"
        file_path.write_text(f"a,b\n1,{'x' * 200_000}\n", encoding="utf-8")

        with pytest.raises(DataIoError) as exc_info:
            list(read_csv(file_path))

        assert exc_info.value.__cause__ is not None


class TestWriteCsv:
    def test_writes_header_from_first_row_keys_in_order(self, tmp_path: Path) -> None:
        file_path = tmp_path / "out.csv"

        write_csv(
            file_path,
            [
                {"event_name": "signup", "event_count": 2},
                {"event_name": "login", "event_count": 1},
            ],
        )

        # read_bytes: read_text's universal-newline translation would
        # hide the csv module's \r\n line terminator.
        assert file_path.read_bytes() == (
            b"event_name,event_count\r\nsignup,2\r\nlogin,1\r\n"
        )

    def test_round_trips_through_read_csv(self, tmp_path: Path) -> None:
        file_path = tmp_path / "round.csv"
        rows = [{"a": "1", "b": "x,y"}, {"a": "2", "b": 'quote "q"'}]

        write_csv(file_path, rows)

        assert list(read_csv(file_path)) == rows

    def test_empty_rows_raise_no_header_derivable(self, tmp_path: Path) -> None:
        with pytest.raises(DataIoError, match="no rows"):
            write_csv(tmp_path / "none.csv", [])

    def test_row_with_mismatched_keys_raises(self, tmp_path: Path) -> None:
        with pytest.raises(DataIoError, match="row 3"):
            write_csv(
                tmp_path / "bad.csv",
                [{"a": "1", "b": "2"}, {"a": "3", "c": "4"}],
            )

    def test_unwritable_path_passes_os_error_through(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            write_csv(tmp_path / "no_such_dir" / "out.csv", [{"a": "1"}])
