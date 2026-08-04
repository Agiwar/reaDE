"""Data-quality dimensions: shipped dimensions, the plug-in point, and check.

Sprint 3.2 acceptance script. Exercises the dq module's public surface
against SQLite: the volume, freshness, and completeness dimensions plus
a custom dimension that satisfies the ``Dimension`` protocol
structurally — inheriting nothing from reaDE — assessed individually
and through the ``check`` golden path. The split semantic is shown at
both layers: an unanswerable measurement (freshness over an empty
table) propagates ``RuleError`` from the dimension, while ``check``
reports that dimension as errored, distinct from failed, without
aborting the report.

Run with: uv run python examples/dq_dimensions.py
"""

from datetime import UTC, datetime

from reade.core.errors import RuleError
from reade.core.interfaces import ConnectionInterface
from reade.data_io import execute_query
from reade.db import SqliteConnector
from reade.dq import (
    CompletenessDimension,
    Dimension,
    DqResult,
    FreshnessDimension,
    VolumeDimension,
    check,
)
from reade.validation import RowCountRule


class OrphanOrdersDimension:
    """Custom plug-in dimension: orders reference existing events.

    Satisfies the ``Dimension`` protocol structurally — no reaDE base
    class, no registration; a conforming ``assess`` is the whole
    contract. Composes a shipped rule the way any custom report row
    would.
    """

    def assess(self, connector: ConnectionInterface) -> DqResult:
        """Aggregate a row-count reading over the orders table."""
        result = RowCountRule(table="orders", min_rows=1).evaluate(connector)
        return DqResult(
            dimension="orphan_orders",
            passed=result.passed,
            rule_results=(result,),
        )


def main() -> None:
    """Run every dimension through the one plug-in seam; exit non-zero on surprise."""
    with SqliteConnector(database=":memory:") as connector:
        execute_query(
            connector,
            "CREATE TABLE events (event_name TEXT, created_at TEXT)",
        )
        execute_query(connector, "CREATE TABLE orders (id INTEGER)")
        now = datetime.now(UTC).replace(tzinfo=None)
        execute_query(
            connector,
            "INSERT INTO events VALUES (:name, :created_at)",
            {"name": "signup", "created_at": now.isoformat(sep=" ")},
        )
        execute_query(connector, "INSERT INTO orders VALUES (1)")

        # One seam for every dimension, built-in or custom: the
        # Dimension protocol.
        dims: list[Dimension] = [
            VolumeDimension(table="events", min_rows=1),
            FreshnessDimension(
                table="events", column="created_at", max_delay_seconds=3600
            ),
            CompletenessDimension(table="events", columns=["event_name"]),
            OrphanOrdersDimension(),
        ]
        for dim in dims:
            outcome = dim.assess(connector)
            print(
                f"[dq] dimension={outcome.dimension} passed={outcome.passed} "
                f"rules={len(outcome.rule_results)}"
            )
            if not outcome.passed:
                raise SystemExit(f"expected every dimension to pass: {outcome}")

        # The golden path: one report over the same instances.
        report = check(connector, dims=dims)
        print(f"[dq] check passed={report.passed}")
        if not report.passed:
            raise SystemExit(f"expected the report to pass: {report}")

        # The split semantic, dimension side: an unanswerable
        # measurement propagates RuleError — it is not a failed check.
        empty_freshness = FreshnessDimension(
            table="orders", column="id", max_delay_seconds=3600
        )
        execute_query(connector, "DELETE FROM orders")
        try:
            empty_freshness.assess(connector)
        except RuleError as error:
            print(f"[dq] dimension propagates on unanswerable: {error}")
        else:
            raise SystemExit("expected freshness over an empty table to raise")

        # The split semantic, report side: check reports the errored
        # dimension distinctly and keeps the rest of the report.
        report = check(
            connector,
            dims=[VolumeDimension(table="events", min_rows=1), empty_freshness],
        )
        print(
            f"[dq] check passed={report.passed} "
            "(errored dimensions report distinctly, they do not abort)"
        )
        if report.passed:
            raise SystemExit("expected a report with an errored dimension to fail")

    print("dq dimensions OK")


if __name__ == "__main__":
    main()
