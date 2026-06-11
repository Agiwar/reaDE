"""Configuration-related exceptions."""

from reade.core.errors.base import ReadeError


class ConfigError(ReadeError):
    """Raised when loading or parsing a configuration source fails."""
