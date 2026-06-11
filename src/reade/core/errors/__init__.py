"""Exception hierarchy."""

from reade.core.errors.base import ReadeError
from reade.core.errors.config import ConfigError
from reade.core.errors.data_io import DataIoError
from reade.core.errors.db import DbError, NotConnectedError
from reade.core.errors.dq import DqError
from reade.core.errors.sql import SqlError
from reade.core.errors.validation import RuleError

__all__ = [
    "ConfigError",
    "DataIoError",
    "DbError",
    "DqError",
    "NotConnectedError",
    "ReadeError",
    "RuleError",
    "SqlError",
]
