"""Completeness data quality dimension."""

from collections.abc import Sequence

from reade.core.errors.dq import DqError
from reade.core.interfaces.connector import ConnectionInterface
from reade.dq.models import DqResult
from reade.validation import NullCountRule, Rule


class CompletenessDimension:
    """Assesses whether a table's columns are fully populated.

    Composed from the validation layer: one ``null_count`` rule per
    named column under a uniform threshold, aggregated into a
    ``DqResult`` that passes only if every column does. An empty table
    passes — zero rows contain zero NULLs, so every count is defined
    and exact; an empty pipeline is the volume dimension's finding.
    """

    def __init__(self, table: str, columns: Sequence[str], max_nulls: int = 0) -> None:
        """Initialize the dimension.

        Args:
            table: Name of the table to assess.
            columns: Columns that must be populated — one null-count
                rule per column, evaluated and reported in the given
                order.
            max_nulls: Maximum NULL count tolerated in each column.
                The threshold is uniform across the columns; the
                default demands fully populated columns. Per-column
                tuning is another dimension instance.

        Raises:
            DqError: If ``columns`` is empty or a bare string — a
                dimension that measures nothing cannot report, and a
                string would be read as per-character column names.
        """
        if isinstance(columns, str):
            raise DqError(
                "CompletenessDimension columns must be a sequence of "
                f"column names, not the string {columns!r}"
            )
        if not columns:
            raise DqError(
                "CompletenessDimension requires at least one column: a "
                "dimension that measures nothing cannot report"
            )
        self._rules: tuple[Rule, ...] = tuple(
            NullCountRule(table=table, column=column, max_nulls=max_nulls)
            for column in columns
        )

    def assess(self, connector: ConnectionInterface, /) -> DqResult:
        """Assess the dimension against a connected database.

        Args:
            connector: A connected database connector — any
                ``ConnectionInterface`` implementation, protocol-only
                connectors included.

        Returns:
            The aggregated outcome; failed checks are results, not
            exceptions, and rule outcomes follow the constructor's
            column order.

        Raises:
            RuleError: If a composed rule cannot be evaluated —
                propagated, never converted to a failed result, like
                any ``ReadeError`` raised below this layer.
        """
        results = tuple(rule.evaluate(connector) for rule in self._rules)
        return DqResult(
            dimension="completeness",
            passed=all(result.passed for result in results),
            rule_results=results,
        )
