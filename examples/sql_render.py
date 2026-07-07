"""Render-contract example: bind + ident across dialects.

Sprint 2.1 acceptance script. Renders one template for all three
supported dialects — same template, dialect-correct placeholders and
identifier quoting — then executes the SQLite variant with its bound
parameters through the connector's ``connection`` escape hatch.
Executing bound parameters through the SDK itself (``execute_query``)
arrives with the Sprint 2.2 data_io seam.

Run with: uv run python examples/sql_render.py
"""

from pathlib import Path

from reade.core.enums import DbType
from reade.db import SqliteConnector
from reade.sql import render_template

TEMPLATES = Path(__file__).parent / "templates"


def main() -> None:
    """Render across dialects, then prove the SQLite binding end to end."""
    context = {"table": "events", "since": "2026-01-01"}

    # sql: one template, three dialects — values never enter the text.
    for dialect in DbType:
        rendered = render_template(
            "daily_events", dialect, context, search_paths=[TEMPLATES]
        )
        print(f"[{dialect.value}]")
        print(f"  sql:    {' '.join(rendered.sql.split())}")
        print(f"  params: {rendered.params}")

    # db: execute the SQLite variant with its bound parameters. Until
    # the 2.2 params seam lands in execute_query, hand the RenderedQuery
    # to the driver via the documented connection escape hatch.
    with SqliteConnector(database=":memory:") as connector:
        connector.connection.execute(
            "CREATE TABLE events (event_name TEXT, created_at TEXT)"
        )
        connector.connection.executemany(
            "INSERT INTO events VALUES (?, ?)",
            [
                ("signup", "2026-03-01"),
                ("signup", "2026-04-11"),
                ("login", "2026-05-20"),
                ("archived", "2025-11-30"),
            ],
        )
        rendered = render_template(
            "daily_events", connector.db_type, context, search_paths=[TEMPLATES]
        )
        rows = connector.connection.execute(rendered.sql, rendered.params).fetchall()
        print(f"[execute]    {rows}")

    expected = [("signup", 2), ("login", 1)]
    if rows != expected:
        raise SystemExit(f"expected {expected}, got {rows}")
    print("sql render contract OK")


if __name__ == "__main__":
    main()
