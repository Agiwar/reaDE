"""Rule protocol: the validation plug-in point."""

from typing import Protocol

from reade.core.interfaces.connector import ConnectionInterface
from reade.validation.models import RuleResult


class Rule(Protocol):
    """Protocol for validation rules — the custom-rule plug-in point.

    The contract for anything the validation layer can evaluate (and,
    from the dq layer, compose into data-quality dimensions). Any object
    with a conforming ``evaluate`` satisfies it structurally; nothing
    needs to inherit from reaDE. Implementations must keep the
    parameter name ``connector``: the protocol makes keyword calls
    (``evaluate(connector=...)``) legal for every conforming rule, so a
    renamed parameter breaks them at runtime — mypy does not flag the
    rename; stricter checkers reject it as non-conforming.

    Rule outcomes are reported as results, not exceptions: a failed
    check is a ``RuleResult`` with ``passed=False``, never a raise.
    Raising is reserved for evaluation failures — the rule could not
    measure at all. This binds every implementer, ours or foreign.
    """

    def evaluate(self, connector: ConnectionInterface) -> RuleResult:
        """Evaluate the rule against a connected database.

        Args:
            connector: A connected database connector — any
                ``ConnectionInterface`` implementation, protocol-only
                connectors included.

        Returns:
            The rule outcome; a failed check yields ``passed=False``,
            not an exception.

        Raises:
            RuleError: If the rule cannot be evaluated — distinct from
                a failed check, which is a result. ``ReadeError``s from
                lower layers (``SqlError``, ``DbError``,
                ``NotConnectedError``) propagate unchanged.
        """
        ...
