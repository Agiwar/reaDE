"""SQL rendering result model."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RenderedQuery:
    """A rendered SQL statement and the values bound to its placeholders.

    The render contract of the sql module: values passed through the
    ``bind`` filter never appear in ``sql`` — the text carries the
    dialect's PEP 249 placeholder and the value lands in ``params`` under
    the same key. Placeholder style follows the dialect the query was
    rendered for: pyformat (``%(key)s``) for PostgreSQL and MySQL, named
    (``:key``) for SQLite.

    ``params`` is a plain ``dict`` by design: pymysql dispatches its
    parameter escaping on ``isinstance(args, dict)`` and sqlite3 rejects
    non-dict mappings, so a read-only proxy would not execute. Treat it
    as read-only. When handing a query with empty ``params`` to a driver,
    pass ``None`` instead of the empty dict — pyformat drivers %-format
    the statement whenever parameters are present, which would corrupt a
    literal ``%`` in the SQL. Executing bound parameters through the SDK
    itself arrives with the data_io params seam (Sprint 2.2).

    Hashing uses ``sql`` only (``params`` is mutable); equality compares
    both fields.

    Attributes:
        sql: The rendered SQL text — placeholders, never values.
        params: Bound values keyed by placeholder name.
    """

    sql: str
    params: dict[str, Any] = field(hash=False)
