"""Data-freshness delay validation rule."""

from datetime import UTC, date, datetime

from reade.core.errors.validation import RuleError
from reade.core.interfaces.connector import ConnectionInterface
from reade.data_io import execute_query
from reade.sql import render_template
from reade.validation.models import RuleResult


class DelayRule:
    """Checks that a table's newest timestamp is fresh enough.

    Composes the chain below it: renders the ``max_timestamp`` SQL
    template, executes it through the given connector, and measures the
    delay client-side — ``now`` minus the newest value in ``column``,
    in seconds, compared against ``max_delay_seconds``.

    Timezone stance (contract): naive timestamps — database values and
    a caller-supplied ``now`` alike — are assumed UTC; aware values are
    normalized to UTC. Future timestamps yield a negative delay and
    pass. ``date`` values measure from midnight UTC — a today-valued
    column reads up to a day old, erring toward staleness.
    """

    def __init__(
        self,
        table: str,
        column: str,
        max_delay_seconds: float,
        *,
        now: datetime | None = None,
    ) -> None:
        """Initialize the rule.

        Args:
            table: Name of the table to check.
            column: Timestamp column measuring each row's recency.
            max_delay_seconds: Maximum age, in seconds, of the newest
                row for the check to pass.
            now: Fixed reference instant, for deterministic tests and
                replays. Defaults to the client clock in UTC, resolved
                at each ``evaluate`` call.
        """
        self._table = table
        self._column = column
        self._max_delay_seconds = max_delay_seconds
        self._now = now

    def evaluate(self, connector: ConnectionInterface, /) -> RuleResult:
        """Evaluate the rule against a connected database.

        Args:
            connector: A connected database connector — any
                ``ConnectionInterface`` implementation, protocol-only
                connectors included.

        Returns:
            The rule outcome; a delay above the threshold yields
            ``passed=False``, not an exception.

        Raises:
            SqlError: If the query cannot be rendered — a hostile table
                or column name never reaches the database; propagated
                from the sql layer, like any ``ReadeError`` raised
                below this layer (``DbError``, ``NotConnectedError``).
            RuleError: If the newest timestamp cannot be measured — the
                table is empty or the column all NULL (``MAX`` yields
                nothing; an unanswerable check is an evaluation
                failure, not staleness), or a value cannot be read as
                a timestamp.
        """
        rendered = render_template(
            "max_timestamp",
            connector.db_type,
            {"table": self._table, "column": self._column},
        )
        rows = execute_query(connector, rendered.sql, rendered.params)
        value = rows[0][0] if rows else None
        if value is None:
            raise RuleError(
                f"Delay for table {self._table!r} is unanswerable: no "
                f"timestamp in column {self._column!r} (empty table or "
                "all NULL)"
            )
        newest = self._normalize(value)
        now = self._now if self._now is not None else datetime.now(UTC)
        observed = (self._normalize(now) - newest).total_seconds()
        return RuleResult(
            rule="delay",
            passed=observed <= self._max_delay_seconds,
            observed=observed,
            threshold=self._max_delay_seconds,
        )

    def _normalize(self, value: object) -> datetime:
        """Read a timestamp value as an aware UTC datetime.

        Naive values are assumed UTC; aware values convert to UTC.
        Accepts ``datetime``, ``date``, and ISO 8601 strings — the
        shapes the MVP drivers return for timestamp columns.

        Raises:
            RuleError: If the value cannot be read as a timestamp.
        """
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=UTC)
            return value.astimezone(UTC)
        if isinstance(value, date):
            return datetime(value.year, value.month, value.day, tzinfo=UTC)
        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value)
            except ValueError as e:
                raise RuleError(
                    f"Column {self._column!r} value {value!r} is not an "
                    "ISO 8601 timestamp"
                ) from e
            return self._normalize(parsed)
        raise RuleError(
            f"Column {self._column!r} value {value!r} "
            f"({type(value).__name__}) is not a timestamp"
        )
