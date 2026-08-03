"""Null count validation rule."""

from reade.core.errors.base import ReadeError
from reade.core.errors.validation import RuleError
from reade.core.interfaces.connector import ConnectionInterface
from reade.data_io import execute_query
from reade.sql import render_template
from reade.validation.models import RuleResult


class NullCountRule:
    """Checks that a column holds at most a maximum number of NULLs.

    Composes the chain below it: renders the ``null_count`` SQL
    template and executes it through the given connector. Counts only
    the named column — a NULL elsewhere is that column's finding.

    An empty table reports ``observed=0``: zero rows contain zero
    NULLs, so the measure is defined and exact — an empty pipeline is
    the volume dimension's finding, not a completeness error.
    """

    def __init__(self, table: str, column: str, max_nulls: int = 0) -> None:
        """Initialize the rule.

        Args:
            table: Name of the table to check.
            column: Column whose NULLs are counted.
            max_nulls: Maximum NULL count allowed to pass. The default
                demands a fully populated column.
        """
        self._table = table
        self._column = column
        self._max_nulls = max_nulls

    def evaluate(self, connector: ConnectionInterface) -> RuleResult:
        """Evaluate the rule against a connected database.

        Args:
            connector: A connected database connector — any
                ``ConnectionInterface`` implementation, protocol-only
                connectors included.

        Returns:
            The rule outcome; a NULL count above the threshold yields
            ``passed=False``, not an exception.

        Raises:
            SqlError: If the count query cannot be rendered — a hostile
                table or column name never reaches the database;
                propagated from the sql layer, like any ``ReadeError``
                raised below this layer (``DbError``,
                ``NotConnectedError``).
            RuleError: If the query result has no usable count value.
        """
        rendered = render_template(
            "null_count",
            connector.db_type,
            {"table": self._table, "column": self._column},
        )
        rows = execute_query(connector, rendered.sql, rendered.params)
        try:
            observed = int(rows[0][0])
        except ReadeError:
            raise
        except Exception as e:
            raise RuleError(
                f"Null count query for column {self._column!r} of table "
                f"{self._table!r} returned no usable value"
            ) from e
        return RuleResult(
            rule="null_count",
            passed=observed <= self._max_nulls,
            observed=observed,
            threshold=self._max_nulls,
        )
