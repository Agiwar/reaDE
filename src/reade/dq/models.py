"""Data quality result models."""

from dataclasses import dataclass

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
    """

    dimension: str
    passed: bool
    rule_results: tuple[RuleResult, ...]
