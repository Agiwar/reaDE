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
    as read-only. Executing through the SDK —
    ``execute_query(connector, rendered.sql, rendered.params)`` — is
    safe even when ``params`` is empty: connectors normalize falsy
    params to no-parameters, per the ``ConnectionInterface`` contract.
    Only when bypassing the SDK via the ``connection`` escape hatch
    must callers pass ``None`` instead of the empty dict — pyformat
    drivers %-format the statement whenever parameters are present,
    which would corrupt a literal ``%`` in the SQL.

    Hashing uses ``sql`` only (``params`` is mutable); equality compares
    both fields.

    Attributes:
        sql: The rendered SQL text — placeholders, never values.
        params: Bound values keyed by placeholder name.

    Stability: stable.
    """

    sql: str
    params: dict[str, Any] = field(hash=False)
