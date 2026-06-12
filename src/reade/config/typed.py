"""Typed loading layer on top of the frozen dict-based loaders."""

from pathlib import Path

from pydantic import BaseModel, ValidationError

from reade.config.factory import ConfigLoaderFactory
from reade.core.enums.file_type import FileType
from reade.core.errors.config import ConfigError


def load_config[ModelT: BaseModel](name: str | Path, *, model: type[ModelT]) -> ModelT:
    """Load a configuration file and validate it into a typed model.

    Composes the dict layer — loader selected by file suffix via
    ``ConfigLoaderFactory``, content parsed by ``ConfigLoader.load`` — with
    pydantic validation on top. pydantic types stop at this boundary:
    validation failures surface as ``ConfigError``, and the resulting
    model's field values are passed on as plain parameters.

    Args:
        name: Path to the configuration file.
        model: The pydantic model class to validate the content against.

    Returns:
        A validated instance of ``model``.

    Raises:
        OSError: If the file cannot be read (including
            ``FileNotFoundError``); passed through unchanged.
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
    path = Path(name)
    try:
        file_type = FileType(path.suffix.lower())
    except ValueError as e:
        raise ConfigError(
            f"No loader registered for file suffix {path.suffix!r}"
        ) from e

    data = ConfigLoaderFactory.get_loader(file_type).load(path)
    try:
        return model.model_validate(data)
    except ValidationError as e:
        raise ConfigError(f"Invalid config {str(path)!r}:\n{e}") from e
