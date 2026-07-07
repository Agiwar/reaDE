"""Jinja2 filters and the per-render state behind them."""

import re
from contextvars import ContextVar
from typing import Any

from jinja2 import Undefined

from reade.core.errors.sql import SqlError
from reade.sql._dialect import _Dialect

_KEY_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

_COLLECTION_TYPES = (list, tuple, set, frozenset, dict)


def _same_value(existing: object, value: object) -> bool:
    """Equality that never crosses types (1, 1.0, and True stay distinct)."""
    return type(existing) is type(value) and bool(existing == value)


class _RenderState:
    """Per-render accumulator for bound parameters.

    One instance lives for exactly one ``render_template`` call. It is
    published to the filters through ``_ACTIVE_STATE`` so the shared,
    cached ``Environment`` stays safe across concurrent renders.
    """

    def __init__(self, dialect: _Dialect) -> None:
        """Initialize empty state for one render in the given dialect."""
        self.dialect = dialect
        self.params: dict[str, Any] = {}
        self._auto_keys: set[str] = set()

    def register_auto(self, value: Any) -> str:
        """Register a value under an automatic key and return the key.

        Auto binds deduplicate among themselves: a value equal to (and of
        the same type as) an already auto-bound one reuses its key rather
        than adding a duplicate parameter. Fresh keys count up ``p0, p1,
        …``, skipping any key already taken.
        """
        for key, existing in self.params.items():
            if key in self._auto_keys and _same_value(existing, value):
                return key
        number = 0
        while f"p{number}" in self.params:
            number += 1
        key = f"p{number}"
        self._auto_keys.add(key)
        self.params[key] = value
        return key

    def register_named(self, name: str, value: Any) -> str:
        """Register a value under a requested key and return the key used.

        Re-binding a key with an equal value of the same type reuses it;
        a different value takes the first free ``name_K`` suffix, so
        loops stay collision-free and keys stay deterministic.
        """
        candidate = name
        suffix = 1
        while candidate in self.params:
            if _same_value(self.params[candidate], value):
                return candidate
            candidate = f"{name}_{suffix}"
            suffix += 1
        self.params[candidate] = value
        return candidate


_ACTIVE_STATE: ContextVar[_RenderState] = ContextVar("reade_sql_render_state")


def bind_filter(value: Any, name: str | None = None) -> str:
    """Register a value as a bound parameter and emit its placeholder.

    Registered on the rendering environment as ``bind``. The value never
    enters the SQL text: it lands in ``RenderedQuery.params`` under the
    chosen key, type-preserved, and the dialect's PEP 249 placeholder is
    rendered in its place.

    Args:
        value: The parameter value, stored as-is.
        name: Optional explicit parameter key. Defaults to automatic
            ``p0, p1, …`` numbering.

    Returns:
        The placeholder text for the registered key.

    Raises:
        SqlError: If the value is a collection (bind scalars — collection
            binding is dialect-specific and not supported), or the key
            fails the ``[A-Za-z_][A-Za-z0-9_]*`` allowlist.
    """
    if isinstance(value, Undefined):
        value._fail_with_undefined_error()
    if isinstance(value, _COLLECTION_TYPES):
        raise SqlError(
            f"bind does not support collection values, got "
            f"{type(value).__name__}; bind scalars individually"
        )
    state = _ACTIVE_STATE.get()
    if name is None:
        key = state.register_auto(value)
    else:
        if not isinstance(name, str) or not _KEY_PATTERN.fullmatch(name):
            raise SqlError(
                f"Invalid bind name {name!r}: bind names must match "
                "[A-Za-z_][A-Za-z0-9_]*"
            )
        key = state.register_named(name, value)
    return state.dialect.placeholder(key)
