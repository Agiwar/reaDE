"""Environment-variable overrides for configuration data."""

import copy
import os
from collections.abc import Mapping
from typing import Any

_PREFIX = "READE__"
_DELIMITER = "__"


def merge_env_overrides(
    data: dict[str, Any],
    environ: Mapping[str, str] = os.environ,
    *,
    scope: str | None = None,
) -> dict[str, Any]:
    """Merge ``READE__``-prefixed environment variables into config data.

    Convention: ``READE__SECTION__KEY`` — prefix ``READE``, nesting
    delimiter ``__``, case-insensitive match against existing config
    keys. Single underscores stay inside key names
    (``READE__DB__MAX_RETRIES`` → ``db.max_retries``). Values are
    inserted as raw strings: type coercion and error reporting are the
    typed layer's job during validation, never this function's.
    Precedence: an environment value overrides the file value — the only
    precedence rule. Variables apply in sorted name order, so when one
    override's path prefixes another's (``READE__DB`` and
    ``READE__DB__HOST``) the deeper path lands last and wins where they
    overlap, regardless of environment iteration order.

    Scoping: with ``scope`` given (e.g. ``"POSTGRES"``), only
    ``READE__POSTGRES__*`` variables apply, and the scope segment is
    stripped before the merge — ``READE__POSTGRES__HOST`` overrides
    ``host``. Variables outside the scope, including bare ``READE__*``
    ones, are ignored: scoping is the namespace isolation that lets
    several config models share one process environment. The scope
    segment is matched exactly (environment variable names are
    case-sensitive; the convention is uppercase).

    The merge is pure: ``data`` is not mutated. Keys with no
    case-insensitive match are inserted lowercased, so env-only values
    work and typo'd variables reach validation, where models reject
    unknown fields (``extra="forbid"``) with a field path instead of
    silently ignoring them. If an intermediate key holds a non-mapping
    value, the override replaces it with a nested mapping (env
    overrides file).

    Args:
        data: Parsed configuration data.
        environ: Environment mapping; injectable for tests. Defaults to
            ``os.environ``.
        scope: Namespace segment restricting which variables apply;
            ``None`` (the default) applies every ``READE__*`` variable.

    Returns:
        A new dictionary with the overrides applied.
    """
    if scope is not None:
        namespace = f"{_PREFIX}{scope}{_DELIMITER}"
        environ = {
            _PREFIX + var.removeprefix(namespace): value
            for var, value in environ.items()
            if var.startswith(namespace) and len(var) > len(namespace)
        }
    result = copy.deepcopy(data)
    for var, value in sorted(environ.items()):
        if not var.startswith(_PREFIX):
            continue
        *parents, leaf = var.removeprefix(_PREFIX).split(_DELIMITER)

        node = result
        for segment in parents:
            key = _matching_key(node, segment)
            if not isinstance(node.get(key), dict):
                node[key] = {}
            node = node[key]
        node[_matching_key(node, leaf)] = value
    return result


def _matching_key(node: dict[str, Any], segment: str) -> str:
    """Return the existing key matching ``segment`` case-insensitively.

    Falls back to the lowercased segment when no key matches, so the
    override is inserted rather than dropped.

    Args:
        node: The mapping to search.
        segment: One ``__``-delimited piece of an override variable name.

    Returns:
        The matched existing key, or the lowercased segment.
    """
    lowered = segment.lower()
    for existing in node:
        if isinstance(existing, str) and existing.lower() == lowered:
            return existing
    return lowered
