"""Rule protocol: the validation plug-in point."""

from typing import Protocol

from reade.core.interfaces.connector import ConnectionInterface
from reade.validation.models import RuleResult


class Rule(Protocol):
    """Protocol for validation rules — the custom-rule plug-in point.

    The contract for anything the validation layer can evaluate (and,
    from the dq layer, compose into data-quality dimensions). Any object
    with a conforming ``evaluate`` satisfies it structurally; nothing
    needs to inherit from reaDE. ``evaluate``'s parameters are
    positional-only: rules are called ``rule.evaluate(connector)``, so
    implementations may name the parameter freely — there is no keyword
    call for a rename to break.

    Rule outcomes are reported as results, not exceptions: a failed
    check is a ``RuleResult`` with ``passed=False``, never a raise.
    Raising is reserved for evaluation failures — the rule could not
    measure at all. This binds every implementer, ours or foreign.

    Stability: stable.
    """

    def evaluate(self, connector: ConnectionInterface, /) -> RuleResult:
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
