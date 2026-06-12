"""Row count validation rule."""

from typing import Any

from reade.core.base.connector import ConnectionBase
from reade.core.errors.base import ReadeError
from reade.core.errors.validation import RuleError
from reade.data_io.execute import execute_query
from reade.sql.render import render_template
from reade.validation.models import RuleResult


class RowCountRule:
    """Checks that a table holds at least a minimum number of rows.

    Composes the chain below it: renders the ``row_count`` SQL template
    and executes it through the given connector.
    """

    def __init__(self, table: str, min_rows: int = 1) -> None:
        """Initialize the rule.

        Args:
            table: Name of the table to count.
            min_rows: Minimum row count required to pass.
        """
        self._table = table
        self._min_rows = min_rows

    def evaluate(self, connector: ConnectionBase[Any]) -> RuleResult:
        """Evaluate the rule against a connected database.

        Args:
            connector: A connected database connector.

        Returns:
            The rule outcome; a count below the threshold yields
            ``passed=False``, not an exception.

        Raises:
            SqlError: If the count query cannot be rendered; propagated
                from the sql layer, like any ``ReadeError`` raised below
                this layer (``DataIoError``, ``NotConnectedError``).
            RuleError: If the query result has no usable count value.
        """
        sql = render_template("row_count", table=self._table)
        rows = execute_query(connector, sql)
        try:
            observed = int(rows[0][0])
        except ReadeError:
            raise
        except Exception as e:
            raise RuleError(
                f"Row count query for table {self._table!r} returned no usable value"
            ) from e
        return RuleResult(
            rule="row_count",
            passed=observed >= self._min_rows,
            observed=observed,
            threshold=self._min_rows,
        )
