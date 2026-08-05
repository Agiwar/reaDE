"""Dimension protocol: the dq plug-in point."""

from typing import Protocol

from reade.core.interfaces.connector import ConnectionInterface
from reade.dq.models import DqResult


class Dimension(Protocol):
    """Protocol for data-quality dimensions — the custom-dimension plug-in point.

    The contract for anything the dq layer can assess and aggregate
    into a report. Any object with a conforming ``assess`` satisfies it
    structurally; nothing needs to inherit from reaDE. ``assess``'s
    parameters are positional-only: dimensions are called
    ``dimension.assess(connector)``, so implementations may name the
    parameter freely — there is no keyword call for a rename to break.

    A dimension composes one or more validation rules and reports
    their aggregated outcome: a failed assessment is a ``DqResult``
    with ``passed=False``, never a raise. Raising is reserved for
    evaluation failures — a composed rule that cannot measure raises
    ``RuleError``, and the dimension lets it propagate; deciding what
    an unanswerable measurement means for a report belongs to the
    reporting layer above, not to the dimension. This binds every
    implementer, ours or foreign.
    """

    def assess(self, connector: ConnectionInterface, /) -> DqResult:
        """Assess the dimension against a connected database.

        Args:
            connector: A connected database connector — any
                ``ConnectionInterface`` implementation, protocol-only
                connectors included.

        Returns:
            The aggregated outcome; a failed assessment yields
            ``passed=False``, not an exception.

        Raises:
            RuleError: If a composed rule cannot be evaluated —
                propagated, never converted to a failed result.
                ``ReadeError``s from lower layers (``SqlError``,
                ``DbError``, ``NotConnectedError``) propagate
                unchanged.
        """
        ...
