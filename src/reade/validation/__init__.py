"""Validation: rules that check data against expectations."""

from reade.validation.models import RuleResult
from reade.validation.rules.count import RowCountRule

__all__ = ["RowCountRule", "RuleResult"]
