"""SQL template rendering."""

import re
from collections.abc import Mapping, Sequence
from functools import lru_cache
from pathlib import Path
from typing import Any

from jinja2 import (
    BaseLoader,
    ChoiceLoader,
    Environment,
    FileSystemLoader,
    PackageLoader,
    StrictUndefined,
    TemplateError,
    TemplateNotFound,
)

from reade.core.enums.db_type import DbType
from reade.core.errors.sql import SqlError
from reade.sql._dialect import _DIALECTS
from reade.sql._filters import _ACTIVE_STATE, _RenderState, bind_filter
from reade.sql.models import RenderedQuery

_PYFORMAT_TOKEN = re.compile(r"%\([A-Za-z_][A-Za-z0-9_]*\)s|%%|%")


@lru_cache(maxsize=16)
def _build_environment(search_paths: tuple[str, ...]) -> Environment:
    """Build and cache the environment for one search-path tuple.

    Jinja compiles templates per environment, so environments are cached
    (bounded — distinct search-path tuples are few in practice; eviction
    only costs recompilation) and ``auto_reload`` still picks up file
    edits. The filters hold no state — per-render state travels through
    ``_ACTIVE_STATE`` — so a shared environment is render-safe.
    """
    loaders: list[BaseLoader] = [PackageLoader("reade.sql", "templates")]
    if search_paths:
        loaders.append(FileSystemLoader(search_paths))
    # autoescape stays off: these templates produce SQL, not HTML/XML,
    # and markup-escaping would corrupt the rendered statements.
    env = Environment(  # noqa: S701  # nosec B701
        loader=ChoiceLoader(loaders),
        undefined=StrictUndefined,
    )
    env.filters["bind"] = bind_filter
    return env


def render_template(
    template_name: str,
    dialect: DbType,
    context: Mapping[str, Any] | None = None,
    /,
    *,
    search_paths: Sequence[str | Path] | None = None,
) -> RenderedQuery:
    """Render a SQL template into a statement and its bound parameters.

    Looks up ``<template_name>.sql.j2`` in the packaged templates and, if
    given, in ``search_paths`` — packaged names always win, so a caller
    directory cannot shadow a packaged template. Values passed through
    the template's ``bind`` filter never appear in the SQL text: each
    lands in ``RenderedQuery.params`` and the dialect's PEP 249
    placeholder — pyformat ``%(key)s`` for PostgreSQL/MySQL, named
    ``:key`` for SQLite — is emitted in its place at render time, with
    no post-render translation. Undefined template variables are errors,
    not silent blanks.

    Trust model: templates are code, context is data. Render only
    templates from directories you control; pass untrusted values
    through ``bind``.

    Args:
        template_name: Bare template name (e.g., ``"row_count"``).
        dialect: Database dialect to render placeholders for.
        context: Template variables.
        search_paths: Additional template directories, searched after
            the packaged directory.

    Returns:
        The rendered statement and its bound parameters.

    Raises:
        SqlError: If the template does not exist, fails to parse or
            render, or references a variable not supplied in ``context``
            (the original Jinja2 exception is attached as the cause); if
            ``bind`` is misused (collection value, invalid key, or a
            placeholder missing from the rendered text); or if a
            parameterized pyformat statement contains a stray ``%`` that
            must be written ``%%``.
    """
    resolved = (
        tuple(str(Path(path).resolve()) for path in search_paths)
        if search_paths
        else ()
    )
    env = _build_environment(resolved)
    filename = f"{template_name}.sql.j2"
    try:
        template = env.get_template(filename)
    except TemplateNotFound as e:
        searched = ", ".join(("reade.sql:templates", *resolved))
        raise SqlError(
            f"SQL template {template_name!r} not found: no {filename} in {searched}"
        ) from e
    except TemplateError as e:
        raise SqlError(f"Failed to load SQL template {template_name!r}") from e

    state = _RenderState(_DIALECTS[dialect])
    token = _ACTIVE_STATE.set(state)
    try:
        sql = template.render(dict(context or {}))
    except TemplateError as e:
        raise SqlError(f"Failed to render SQL template {template_name!r}") from e
    finally:
        _ACTIVE_STATE.reset(token)

    _check_placeholders(sql, state)
    _check_percent_literals(sql, state)
    return RenderedQuery(sql=sql, params=dict(state.params))


def _check_placeholders(sql: str, state: _RenderState) -> None:
    """Ensure every registered parameter's placeholder survived rendering.

    Catches bind results that were transformed after binding (e.g. a
    later filter in the chain) or discarded without being emitted —
    errors that would otherwise surface only at execution time, two
    sprints away from their cause.
    """
    missing = []
    for key in state.params:
        pattern = re.escape(state.dialect.placeholder(key))
        if not state.dialect.pyformat:
            # ':p1' must not be satisfied by ':p10'; pyformat's ')s'
            # already delimits the key.
            pattern += r"(?![A-Za-z0-9_])"
        if not re.search(pattern, sql):
            missing.append(key)
    if missing:
        raise SqlError(
            f"Bound parameter(s) {missing} have no placeholder in the rendered "
            "SQL; apply bind last in a filter chain and emit its result into "
            "the statement"
        )


def _check_percent_literals(sql: str, state: _RenderState) -> None:
    """Reject stray ``%`` in parameterized pyformat SQL at render time.

    pyformat drivers %-format the statement whenever parameters are
    passed, so a lone ``%`` (as in ``LIKE '%x%'``) fails at execution
    with an unrelated driver error. Requiring ``%%`` here turns that
    into an immediate, explainable failure. Statements with no bound
    parameters are exempt — they execute with ``params=None`` and are
    never %-formatted.
    """
    if not state.dialect.pyformat or not state.params:
        return
    for match in _PYFORMAT_TOKEN.finditer(sql):
        if match.group() == "%":
            raise SqlError(
                "Literal '%' in a parameterized query must be written '%%' "
                f"for this dialect (position {match.start()})"
            )
