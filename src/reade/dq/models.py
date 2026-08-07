"""Data quality result models."""

from dataclasses import dataclass

from reade.core.errors.validation import RuleError
from reade.validation import RuleResult


@dataclass(frozen=True)
class DqResult:
    """Outcome of assessing a data quality dimension.

    A dimension aggregates one or more validation rule outcomes; like
    them, a failed assessment is a result, never a raise.

    Attributes:
        dimension: Name of the assessed dimension.
        passed: Whether every underlying rule passed.
        rule_results: The individual rule outcomes the dimension
            aggregated.

    Stability: stable.
    """

    dimension: str
    passed: bool
    rule_results: tuple[RuleResult, ...]


@dataclass(frozen=True)
class DqReport:
    """Outcome of a data-quality check across dimensions.

    One entry per dimension, in the order given to ``check``: a
    ``DqResult`` where the dimension measured, or the ``RuleError``
    that made its measurement unanswerable. Errored entries carry
    their error and are never represented as failed results — errored
    and failed stay distinct. The report passes only if every
    dimension measured and passed.

    Attributes:
        passed: Whether every dimension measured and passed.
        entries: Per-dimension outcomes in input order — a
            ``DqResult`` for each measured dimension, the caught
            ``RuleError`` for each errored one.

    Stability: stable.
    """

    passed: bool
    entries: tuple[DqResult | RuleError, ...]
