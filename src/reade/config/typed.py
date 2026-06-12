"""Typed loading layer on top of the frozen dict-based loaders."""

import os
from collections.abc import Mapping, Sequence
from pathlib import Path

from pydantic import BaseModel, ValidationError

from reade.config.env import merge_env_overrides
from reade.config.factory import ConfigLoaderFactory
from reade.core.enums.file_type import FileType
from reade.core.errors.config import ConfigError


def load_config[ModelT: BaseModel](
    name: str | Path,
    *,
    model: type[ModelT],
    search_paths: Sequence[str | Path] | None = None,
    environ: Mapping[str, str] | None = None,
) -> ModelT:
    """Load a configuration file and validate it into a typed model.

    The full flow: resolve ``name`` against ``search_paths`` → parse via
    the dict layer (loader selected by file suffix through
    ``ConfigLoaderFactory``, content parsed by ``ConfigLoader.load``) →
    apply ``READE__``-prefixed environment overrides (see
    ``merge_env_overrides``) → validate. pydantic types stop at this
    boundary: validation failures surface as ``ConfigError``, and the
    resulting model's field values are passed on as plain parameters.

    Resolution: an absolute ``name`` bypasses the search entirely. A
    relative ``name`` is tried against each directory in ``search_paths``
    in order; the first hit wins. The default is the current working
    directory only — Python's own relative-path baseline. The SDK reads
    no environment variables for file location; applications wanting an
    env-var convention pass ``os.environ[...]`` into ``search_paths``
    themselves.

    Override scoping: a model may declare ``env_prefix`` as a non-empty
    string ``ClassVar`` (the shipped models declare ``"SQLITE"``,
    ``"POSTGRES"``, ``"MYSQL"``). When present, only
    ``READE__<PREFIX>__*`` variables apply to that model — the prefix
    segment is stripped before the merge, and everything outside it
    (including bare ``READE__*`` variables) is ignored. Models without
    an ``env_prefix`` get the unscoped behavior: every ``READE__*``
    variable applies. This ClassVar is the extension contract for
    third-party models; declaring it as a pydantic *field* is rejected
    (it would silently change which variables apply).

    Args:
        name: Configuration file path or name to resolve.
        model: The pydantic model class to validate the content against.
        search_paths: Directories (``str`` or ``Path``) to try for a
            relative ``name``, in order. Defaults to the current working
            directory, resolved at call time.
        environ: Environment mapping consulted for ``READE__`` overrides.
            Defaults to ``os.environ``, where overrides apply
            process-wide — every ``load_config`` call sees the same
            ``READE__*`` variables. Pass ``{}`` to disable overrides for
            a call, or a filtered mapping to scope which variables apply.

    Returns:
        A validated instance of ``model``.

    Raises:
        FileNotFoundError: If a relative ``name`` is not found in any
            search path; the message lists every directory searched.
        OSError: If the file cannot be read; passed through unchanged
            (including ``FileNotFoundError`` for a missing absolute
            ``name``).
        ConfigError: If no loader is registered for the file's suffix, the
            content cannot be parsed, validation fails, or the model
            declares an invalid ``env_prefix`` (a pydantic field instead
            of a ClassVar, a non-string, or an empty string). Validation
            failures carry pydantic's field-path report in the message,
            with the original ``ValidationError`` attached as the cause
            (``raise ... from``).

    Note:
        pydantic turns only ``ValueError``/``AssertionError`` from a
        model's own validators into ``ValidationError``. Any other
        exception type raised by user-owned validator code propagates
        unchanged — deliberately, since wrapping it would mask validator
        bugs as config errors.
    """
    scope = _validated_env_prefix(model)
    path = _resolve_config_path(name, search_paths)
    try:
        file_type = FileType(path.suffix.lower())
    except ValueError as e:
        raise ConfigError(
            f"No loader registered for file suffix {path.suffix!r}"
        ) from e

    data = ConfigLoaderFactory.get_loader(file_type).load(path)
    data = merge_env_overrides(
        data, os.environ if environ is None else environ, scope=scope
    )
    try:
        return model.model_validate(data)
    except ValidationError as e:
        raise ConfigError(f"Invalid config {str(path)!r}:\n{e}") from e


def _validated_env_prefix(model: type[BaseModel]) -> str | None:
    """Return the model's ``env_prefix``, enforcing the ClassVar contract.

    A prefix declared as a pydantic *field* is unreachable on the class
    (pydantic removes field names from class attribute access), so the
    scoping would silently fall back to unscoped behavior — the failure
    mode this guard exists to make loud.

    Args:
        model: The model class whose prefix declaration to validate.

    Returns:
        The declared prefix, or ``None`` for unscoped models.

    Raises:
        ConfigError: If ``env_prefix`` is declared as a pydantic field,
            is not a string, or is empty.
    """
    if "env_prefix" in model.model_fields:
        raise ConfigError(
            f"{model.__name__}.env_prefix must be a ClassVar, not a model "
            "field — as a field it never reaches the scoping layer"
        )
    scope = getattr(model, "env_prefix", None)
    if scope is None:
        return None
    if not isinstance(scope, str) or not scope:
        raise ConfigError(
            f"{model.__name__}.env_prefix must be a non-empty string, got {scope!r}"
        )
    return scope


def _resolve_config_path(
    name: str | Path, search_paths: Sequence[str | Path] | None
) -> Path:
    """Resolve a config file name against the search paths.

    Args:
        name: Configuration file path or name to resolve.
        search_paths: Directories to try in order; ``None`` means the
            current working directory, captured at call time.

    Returns:
        An absolute ``name`` unchanged, or the first ``directory / name``
        that exists as a file.

    Raises:
        FileNotFoundError: If a relative ``name`` is not found in any
            search path; the message lists every directory searched.
    """
    path = Path(name)
    if path.is_absolute():
        return path

    directories = (
        [Path(directory) for directory in search_paths]
        if search_paths is not None
        else [Path.cwd()]
    )
    for directory in directories:
        candidate = directory / path
        if candidate.is_file():
            return candidate

    searched = ", ".join(str(directory) for directory in directories)
    raise FileNotFoundError(
        f"Config file {str(path)!r} not found in search paths: {searched}"
    )
