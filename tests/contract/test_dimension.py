"""Contract tests for the Dimension protocol.

Every dimension implementation must satisfy these guarantees: a failed
assessment is a ``DqResult`` with ``passed=False``, never a raise,
while a composed rule's evaluation failure (``RuleError``) propagates —
a dimension never converts an unanswerable measurement into a verdict.
The protocol-only dimension below is the plug-in-promise contract one
layer above the rules: a structural implementation that inherits
nothing from reaDE must satisfy the protocol and assess through the
same seam as the shipped dimensions.
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
from reade.dq import (
    CompletenessDimension,
    Dimension,
    DqResult,
    FreshnessDimension,
    VolumeDimension,
    check,
)
from reade.validation import NullCountRule, RowCountRule

# Static conformance proofs: mypy verifies on these assignments that
# every shipped dimension satisfies the protocol.
_volume_conformance: Dimension = VolumeDimension(table="events")
_freshness_conformance: Dimension = FreshnessDimension(
    table="events", column="created_at", max_delay_seconds=3600
)
_completeness_conformance: Dimension = CompletenessDimension(
    table="events", columns=["event_name"]
)


class PopulatedRowsDimension:
    """A third-party-style dimension satisfying the protocol structurally.

    Inherits nothing from reaDE; a conforming ``assess`` is the whole
    contract. Composes shipped rules the way any custom report row
    would, aggregating a genuinely multi-rule outcome.
    """

    def __init__(self, table: str, column: str) -> None:
        self._rules: tuple[RowCountRule, NullCountRule] = (
            RowCountRule(table=table),
            NullCountRule(table=table, column=column),
        )

    def assess(self, connector: ConnectionInterface) -> DqResult:
        """Aggregate row-count and null-count outcomes into one verdict."""
        results = tuple(rule.evaluate(connector) for rule in self._rules)
        return DqResult(
            dimension="populated_rows",
            passed=all(result.passed for result in results),
            rule_results=results,
        )


# Static conformance proof for the protocol-only dimension.
_protocol_only_conformance: Dimension = PopulatedRowsDimension(
    table="events", column="event_name"
)


class NoRowsConnector:
    """A connector stub whose ``execute`` returns no rows at all.

    Structurally satisfies ``ConnectionInterface`` so a composed rule's
    evaluation failure can be driven through a dimension without a
    database.
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
        execute_query(conn, "CREATE TABLE events (event_name TEXT)")
        execute_query(
            conn,
            "INSERT INTO events VALUES ('signup'), ('login'), ('logout')",
        )
        yield conn


class TestDimensionProtocol:
    def test_protocol_only_dimension_assesses_through_the_seam(
        self, connector: SqliteConnector
    ) -> None:
        dimension: Dimension = PopulatedRowsDimension(
            table="events", column="event_name"
        )

        outcome = dimension.assess(connector)

        assert outcome.passed
        assert outcome.dimension == "populated_rows"
        assert len(outcome.rule_results) == 2
        assert all(result.passed for result in outcome.rule_results)

    def test_failed_assessment_is_result_not_exception(
        self, connector: SqliteConnector
    ) -> None:
        outcome = VolumeDimension(table="events", min_rows=100).assess(connector)

        assert not outcome.passed
        assert outcome.rule_results[0].observed == 3
        assert outcome.rule_results[0].threshold == 100

    def test_rule_error_propagates_through_a_dimension(self) -> None:
        # A composed rule that cannot measure raises RuleError, and the
        # dimension lets it propagate: an unanswerable measurement is
        # not a verdict — the split semantic's dimension half.
        with pytest.raises(RuleError):
            VolumeDimension(table="events").assess(NoRowsConnector())

    def test_keyword_call_is_rejected_positional_only(
        self, connector: SqliteConnector
    ) -> None:
        # The protocol's parameters are positional-only: there is no
        # keyword call for a parameter rename to break, so the name-lock
        # contract is retired — a keyword call is a TypeError against
        # every conforming dimension.
        dimension: Dimension = VolumeDimension(table="events")

        with pytest.raises(TypeError):
            # The static error is the contract working; the runtime
            # assertion proves the same rejection without a checker.
            dimension.assess(connector=connector)  # type: ignore[call-arg]

    def test_protocol_only_dimension_reports_through_check(
        self, connector: SqliteConnector
    ) -> None:
        # The plug-in promise at the golden path: a custom dimension
        # that inherits nothing from reaDE reports through check next
        # to a shipped one, in input order.
        report = check(
            connector,
            dims=[
                PopulatedRowsDimension(table="events", column="event_name"),
                VolumeDimension(table="events"),
            ],
        )

        assert report.passed
        first = report.entries[0]
        assert isinstance(first, DqResult)
        assert first.dimension == "populated_rows"
        assert len(first.rule_results) == 2
