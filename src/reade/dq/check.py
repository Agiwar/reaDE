"""The data-quality golden path."""

from collections.abc import Sequence

from reade.core.errors.dq import DqError
from reade.core.errors.validation import RuleError
from reade.core.interfaces.connector import ConnectionInterface
from reade.dq.interfaces import Dimension
from reade.dq.models import DqReport, DqResult


def check(connector: ConnectionInterface, dims: Sequence[Dimension]) -> DqReport:
    """Assess dimensions against one connection and aggregate one report.

    The opinionated golden path: every dimension assesses through the
    given connector, and the outcomes aggregate into one ``DqReport``.
    A dimension whose measurement is unanswerable (``RuleError``) is
    reported as errored — its entry carries the error, distinct from a
    failed check — and the report keeps every other dimension's
    verdict instead of aborting.

    Args:
        connector: A connected database connector — any
            ``ConnectionInterface`` implementation, protocol-only
            connectors included.
        dims: Dimensions to assess, shipped or custom — anything
            satisfying the ``Dimension`` protocol. Report entries
            follow this order.

    Returns:
        The aggregated report; it passes only if every dimension
        measured and passed. Failed and errored dimensions are report
        entries, never a raise.

    Raises:
        DqError: If ``dims`` is empty — a report over zero dimensions
            would pass vacuously; a check that measures nothing cannot
            report.
        ReadeError: From layers below the dimensions, propagated
            unchanged — only ``RuleError`` is caught and reported:
            ``SqlError`` (a hostile identifier is a caller bug, not a
            data condition) and ``DbError`` (a dead connection aborts
            the report), ``NotConnectedError`` included, pass through.

    Stability: stable.
    """
    if not dims:
        raise DqError(
            "check requires at least one dimension: a report that "
            "measures nothing cannot pass"
        )
    entries: list[DqResult | RuleError] = []
    passed = True
    for dim in dims:
        try:
            result = dim.assess(connector)
        except RuleError as error:
            entries.append(error)
            passed = False
        else:
            entries.append(result)
            passed = passed and result.passed
    return DqReport(passed=passed, entries=tuple(entries))
