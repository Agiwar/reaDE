"""Validation rules: the built-in rules and the custom-rule plug-in point.

Sprint 3.1 acceptance script. Exercises the validation module's public
surface against SQLite: the row-count, delay, and null-count rules, plus
a custom rule that satisfies the ``Rule`` protocol structurally —
inheriting nothing from reaDE — evaluated through the same seam. Rule
outcomes are results, not exceptions: the deliberately failing check at
the end reports ``passed=False`` instead of raising.

Run with: uv run python examples/validation_rules.py
"""

from datetime import UTC, datetime

from reade.core.interfaces import ConnectionInterface
from reade.data_io import execute_query
from reade.db import SqliteConnector
from reade.validation import (
    DelayRule,
    NullCountRule,
    RowCountRule,
    Rule,
    RuleResult,
)


class DistinctEventsRule:
    """Custom plug-in rule: distinct event names meet a minimum.

    Satisfies the ``Rule`` protocol structurally — no reaDE base class,
    no registration; a conforming ``evaluate`` is the whole contract.
    """

    def __init__(self, min_distinct: int = 1) -> None:
        """Initialize the rule.

        Args:
            min_distinct: Minimum distinct event names required to pass.
        """
        self._min_distinct = min_distinct

    def evaluate(self, connector: ConnectionInterface) -> RuleResult:
        """Count distinct event names in the ``events`` table."""
        rows = execute_query(connector, "SELECT COUNT(DISTINCT event_name) FROM events")
        observed = int(rows[0][0])
        return RuleResult(
            rule="distinct_events",
            passed=observed >= self._min_distinct,
            observed=observed,
            threshold=self._min_distinct,
        )


def main() -> None:
    """Run every rule through the one plug-in seam; exit non-zero on surprise."""
    with SqliteConnector(database=":memory:") as connector:
        execute_query(
            connector, "CREATE TABLE events (event_name TEXT, created_at TEXT)"
        )
        # Naive UTC timestamps — the delay rule's documented stance.
        now = datetime.now(UTC).replace(tzinfo=None)
        execute_query(
            connector,
            "INSERT INTO events VALUES (:name, :created_at)",
            {"name": "signup", "created_at": now.isoformat(sep=" ")},
        )

        # One seam for every rule, built-in or custom: the Rule protocol.
        rules: list[Rule] = [
            RowCountRule(table="events", min_rows=1),
            DelayRule(table="events", column="created_at", max_delay_seconds=3600),
            NullCountRule(table="events", column="event_name", max_nulls=0),
            DistinctEventsRule(min_distinct=1),
        ]
        results = [rule.evaluate(connector) for rule in rules]
        for result in results:
            print(
                f"[validation] rule={result.rule} passed={result.passed} "
                f"observed={result.observed} threshold={result.threshold}"
            )
        if not all(result.passed for result in results):
            raise SystemExit(f"expected every rule to pass: {results}")

        # Results, not exceptions: a failed check reports passed=False.
        failed = RowCountRule(table="events", min_rows=100).evaluate(connector)
        print(
            f"[validation] rule={failed.rule} passed={failed.passed} "
            "(failing checks report, they do not raise)"
        )
        if failed.passed:
            raise SystemExit("expected the min_rows=100 check to fail as a result")

    print("validation rules OK")


if __name__ == "__main__":
    main()
