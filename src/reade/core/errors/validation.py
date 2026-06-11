"""Validation exceptions."""

from reade.core.errors.base import ReadeError


class ValidationError(ReadeError):
    """Raised when evaluating a validation rule fails.

    Signals that a rule could not be evaluated — not that data failed
    a check; rule outcomes are reported as results, not exceptions.
    """
