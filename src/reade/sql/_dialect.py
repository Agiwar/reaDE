"""Per-dialect SQL syntax: identifier quoting and placeholder style."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

from reade.core.enums.db_type import DbType


@dataclass(frozen=True)
class _Dialect:
    """SQL syntax fragments that differ across the supported databases.

    Attributes:
        quote_char: Character wrapping each quoted identifier part.
        placeholder: Renders a bind key as the dialect's PEP 249
            placeholder.
        pyformat: True when the placeholder style is pyformat, in which
            case a literal ``%`` in parameterized SQL must be escaped as
            ``%%`` for the driver.
    """

    quote_char: str
    placeholder: Callable[[str], str]
    pyformat: bool


def _pyformat_placeholder(key: str) -> str:
    return f"%({key})s"


def _named_placeholder(key: str) -> str:
    return f":{key}"


_DIALECTS: Mapping[DbType, _Dialect] = MappingProxyType(
    {
        DbType.SQLITE: _Dialect(
            quote_char='"', placeholder=_named_placeholder, pyformat=False
        ),
        DbType.MYSQL: _Dialect(
            quote_char="`", placeholder=_pyformat_placeholder, pyformat=True
        ),
        DbType.POSTGRESQL: _Dialect(
            quote_char='"', placeholder=_pyformat_placeholder, pyformat=True
        ),
    }
)
