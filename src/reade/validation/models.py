"""Validation result models."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RuleResult:
    """Outcome of evaluating a validation rule.

    Rule outcomes are reported as results, not exceptions: a failed
    check is a ``RuleResult`` with ``passed=False``, never a raise.

    Attributes:
        rule: Name of the rule that produced this result.
        passed: Whether the data satisfied the rule.
        observed: The value the rule measured.
        threshold: The bound the observed value was compared against.
    """

    rule: str
    passed: bool
    observed: int
    threshold: int
