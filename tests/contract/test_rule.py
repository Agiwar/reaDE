"""Contract tests for the Rule protocol.

Every rule implementation must satisfy these guarantees: rule outcomes
are results, not exceptions — a failed check is a ``RuleResult`` with
``passed=False``, never a raise — while evaluation failures (the rule
could not measure at all) raise ``RuleError``, and ``ReadeError``s from
lower layers propagate unchanged. The protocol-only rule below is the
plug-in-promise contract: a structural implementation that inherits
nothing from reaDE must satisfy the protocol and evaluate through the
same seam as the shipped rules.
"""

from collections.abc import Iterator
from types import TracebackType
from typing import Any, Self

import pytest

from reade.core.enums import DbType
from reade.core.errors import RuleError
from reade.core.interfaces import ConnectionInterface
from reade.data_io import execute_query
from reade.db import SqliteConnector
from reade.validation import RowCountRule, Rule, RuleResult

# Static conformance proof: mypy verifies on this assignment that the
# shipped rule satisfies the protocol.
_shipped_conformance: Rule = RowCountRule(table="events")


class MaxIdRule:
    """A third-party-style rule satisfying the protocol structurally.

    Inherits nothing from reaDE; a conforming ``evaluate`` is the whole
    contract.
    """

    def __init__(self, max_id: int) -> None:
        self._max_id = max_id

    def evaluate(self, connector: ConnectionInterface) -> RuleResult:
        """Check that the highest id does not exceed the threshold."""
        rows = execute_query(connector, "SELECT MAX(id) FROM events")
        observed = int(rows[0][0])
        return RuleResult(
            rule="max_id",
            passed=observed <= self._max_id,
            observed=observed,
            threshold=self._max_id,
        )


# Static conformance proof for the protocol-only rule.
_protocol_only_conformance: Rule = MaxIdRule(max_id=10)


class NoRowsConnector:
    """A connector stub whose ``execute`` returns no rows at all.

    Structurally satisfies ``ConnectionInterface`` so a rule's
    unusable-result branch can be driven without a database.
    """

    db_type = DbType.SQLITE

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None

    def connect(self) -> None:
        return None

    def close(self) -> None:
        return None

    def is_connected(self) -> bool:
        return True

    def ping(self) -> bool:
        return True

    def execute(
        self, sql: str, params: dict[str, Any] | None = None
    ) -> list[tuple[Any, ...]]:
        return []


@pytest.fixture
def connector() -> Iterator[SqliteConnector]:
    with SqliteConnector(database=":memory:") as conn:
        execute_query(conn, "CREATE TABLE events (id INTEGER)")
        execute_query(conn, "INSERT INTO events VALUES (1), (2), (3)")
        yield conn


class TestRuleProtocol:
    def test_protocol_only_rule_evaluates_through_the_seam(
        self, connector: SqliteConnector
    ) -> None:
        result = MaxIdRule(max_id=10).evaluate(connector)

        assert result.passed
        assert result.rule == "max_id"
        assert result.observed == 3
        assert result.threshold == 10

    def test_failed_check_is_result_not_exception(
        self, connector: SqliteConnector
    ) -> None:
        result = MaxIdRule(max_id=2).evaluate(connector)

        assert not result.passed
        assert result.observed == 3
        assert result.threshold == 2

    def test_unusable_result_raises_rule_error(self) -> None:
        # An unusable query result (no rows) is an evaluation failure,
        # not a failed check: RuleError, per the protocol contract.
        with pytest.raises(RuleError):
            RowCountRule(table="events").evaluate(NoRowsConnector())


class TestRuleResultShape:
    def test_durations_and_counts_share_one_result_shape(self) -> None:
        duration = RuleResult(
            rule="delay", passed=True, observed=12.5, threshold=3600.0
        )
        count = RuleResult(rule="row_count", passed=True, observed=3, threshold=1)

        assert duration.observed == 12.5
        assert count.observed == 3
