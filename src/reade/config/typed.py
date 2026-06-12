"""Typed loading layer on top of the frozen dict-based loaders."""

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
    search_paths: tuple[Path, ...] | None = None,
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

    Args:
        name: Configuration file path or name to resolve.
        model: The pydantic model class to validate the content against.
        search_paths: Directories to try for a relative ``name``, in
            order. Defaults to ``(Path.cwd(),)``, resolved at call time.

    Returns:
        A validated instance of ``model``.

    Raises:
        FileNotFoundError: If a relative ``name`` is not found in any
            search path; the message lists every directory searched.
        OSError: If the file cannot be read; passed through unchanged
            (including ``FileNotFoundError`` for a missing absolute
            ``name``).
        ConfigError: If no loader is registered for the file's suffix, the
            content cannot be parsed, or validation fails. Validation
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
    path = _resolve_config_path(name, search_paths)
    try:
        file_type = FileType(path.suffix.lower())
    except ValueError as e:
        raise ConfigError(
            f"No loader registered for file suffix {path.suffix!r}"
        ) from e

    data = ConfigLoaderFactory.get_loader(file_type).load(path)
    data = merge_env_overrides(data)
    try:
        return model.model_validate(data)
    except ValidationError as e:
        raise ConfigError(f"Invalid config {str(path)!r}:\n{e}") from e


def _resolve_config_path(
    name: str | Path, search_paths: tuple[Path, ...] | None
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

    directories = search_paths if search_paths is not None else (Path.cwd(),)
    for directory in directories:
        candidate = directory / path
        if candidate.is_file():
            return candidate

    searched = ", ".join(str(directory) for directory in directories)
    raise FileNotFoundError(
        f"Config file {str(path)!r} not found in search paths: {searched}"
    )
