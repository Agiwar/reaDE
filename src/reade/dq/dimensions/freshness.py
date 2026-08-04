"""Freshness data quality dimension."""

from reade.core.interfaces.connector import ConnectionInterface
from reade.dq.models import DqResult
from reade.validation import DelayRule, Rule


class FreshnessDimension:
    """Assesses whether a table's newest data is recent enough.

    Composed from the validation layer: the ``delay`` rule's freshness
    measurement, aggregated into a ``DqResult``.
    """

    def __init__(self, table: str, column: str, max_delay_seconds: float) -> None:
        """Initialize the dimension.

        Args:
            table: Name of the table to assess.
            column: Timestamp column measuring each row's recency.
            max_delay_seconds: Maximum age, in seconds, of the newest
                row for the assessment to pass.
        """
        self._rule: Rule = DelayRule(
            table=table, column=column, max_delay_seconds=max_delay_seconds
        )

    def assess(self, connector: ConnectionInterface) -> DqResult:
        """Assess the dimension against a connected database.

        Args:
            connector: A connected database connector — any
                ``ConnectionInterface`` implementation, protocol-only
                connectors included.

        Returns:
            The aggregated outcome; failed checks are results, not
            exceptions.

        Raises:
            RuleError: If the composed rule cannot be evaluated — a
                freshness measurement over an empty table (or all-NULL
                column) is unanswerable, not stale — propagated, never
                converted to a failed result, like any ``ReadeError``
                raised below this layer.
        """
        result = self._rule.evaluate(connector)
        return DqResult(
            dimension="freshness",
            passed=result.passed,
            rule_results=(result,),
        )
