"""End-to-end walking skeleton: config → db → sql → data_io → validation → dq.

Sprint 0.2 acceptance script (DoD item 1). Exercises the full dependency
chain against SQLite using only the public API: load a YAML config, open a
connection, render a SQL template, execute it, evaluate a validation rule,
and aggregate it into a data-quality dimension.

Run with: uv run python examples/end_to_end.py
"""

from pathlib import Path

from reade.config import ConfigLoaderFactory
from reade.core.enums import FileType
from reade.data_io import execute_query
from reade.db import SqliteConnector
from reade.dq import VolumeDimension
from reade.sql import render_template
from reade.validation import RowCountRule


def main() -> None:
    """Run the full chain and exit non-zero if the DQ check fails."""
    # config: pick a loader via the factory, parse YAML into a dict.
    config_path = Path(__file__).parent / "config" / "db.yaml"
    loader = ConfigLoaderFactory.get_loader(FileType(config_path.suffix.lower()))
    config = loader.load(config_path)
    print(f"[config]     loaded {config_path.name}: {config}")

    # db: connection lifecycle via context manager (connect on enter,
    # close on exit), with an end-to-end health check.
    with SqliteConnector(database=config["db"]["database"]) as connector:
        print(f"[db]         connected={connector.is_connected()}", end=" ")
        print(f"ping={connector.ping()}")

        # data_io: execute statements through the connector.
        execute_query(
            connector,
            "CREATE TABLE events (id INTEGER PRIMARY KEY, name TEXT)",
        )
        execute_query(
            connector,
            "INSERT INTO events (name) VALUES ('signup'), ('login'), ('logout')",
        )

        # sql: render a packaged Jinja2 template into a SQL string.
        sql = render_template("row_count", table="events")
        rows = execute_query(connector, sql)
        print(f"[sql]        rendered: {sql.strip()}")
        print(f"[data_io]    result rows: {rows}")

        # validation: one rule — row count against a threshold.
        rule_result = RowCountRule(table="events", min_rows=1).evaluate(connector)
        print(
            f"[validation] rule={rule_result.rule} passed={rule_result.passed} "
            f"observed={rule_result.observed} threshold={rule_result.threshold}"
        )

        # dq: the volume dimension, composed from the validation rule.
        dq_result = VolumeDimension(table="events", min_rows=1).assess(connector)
        print(f"[dq]         dimension={dq_result.dimension} passed={dq_result.passed}")

    if not dq_result.passed:
        raise SystemExit(1)
    print("end-to-end chain OK")


if __name__ == "__main__":
    main()
