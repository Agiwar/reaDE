"""Volume data quality dimension."""

from reade.core.interfaces.connector import ConnectionInterface
from reade.dq.models import DqResult
from reade.validation import RowCountRule, Rule


class VolumeDimension:
    """Assesses whether a table holds the expected volume of data.

    Composed from the validation layer: today the dimension is the
    ``row_count`` rule, aggregated into a ``DqResult``.
    """

    def __init__(self, table: str, min_rows: int = 1) -> None:
        """Initialize the dimension.

        Args:
            table: Name of the table to assess.
            min_rows: Minimum row count required to pass.
        """
        self._rule: Rule = RowCountRule(table=table, min_rows=min_rows)

    def assess(self, connector: ConnectionInterface, /) -> DqResult:
        """Assess the dimension against a connected database.

        Args:
            connector: A connected database connector — any
                ``ConnectionInterface`` implementation, protocol-only
                connectors included.

        Returns:
            The aggregated outcome; failed checks are results, not
            exceptions.

        Raises:
            RuleError: If an underlying rule cannot be evaluated;
                propagated from the validation layer, like any
                ``ReadeError`` raised below this layer.
        """
        result = self._rule.evaluate(connector)
        return DqResult(
            dimension="volume",
            passed=result.passed,
            rule_results=(result,),
        )
