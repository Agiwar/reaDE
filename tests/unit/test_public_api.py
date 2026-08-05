"""Public-API contract: smoke imports and the frozen-surface snapshot.

The snapshot test pins the public surface — the ``__all__`` names of
every feature package and core subpackage — and compares the pins
against ``tests/snapshots/public_api.json``. Functions pin as signature
strings; classes pin as their body-defined members plus annotations, so
a member joining a Protocol or ABC trips the pin, not only a top-level
signature change. Abstract members of public ABCs are pinned even when
single-underscore-named: a template-method hook is the extender's
contract, so renaming or reshaping one is an API event.

Pins are textual. Their exact form can vary across Python versions (CI
runs a single version today) and can churn when a dependency that
generates signatures (pydantic above all) upgrades. Such churn is a
representation adjustment: regenerate and review the snapshot diff —
never regenerate silently. A default whose repr embeds runtime state
(``os.environ`` above all) pins as its type name — a raw repr would be
both nondeterministic and an environment leak into a tracked file.

Regenerate: ``uv run python tests/unit/test_public_api.py``.
"""

import importlib
import inspect
import json
import pkgutil
from collections.abc import Mapping
from enum import Enum
from pathlib import Path
from types import ModuleType
from typing import Any

from pydantic import BaseModel

import reade
import reade.core
from reade.core.enums import DbType, FileType
from reade.core.errors import (
    ConfigError,
    DataIoError,
    DbError,
    DqError,
    NotConnectedError,
    ReadeError,
    RuleError,
    SqlError,
)
from reade.core.interfaces import ConfigLoader, ConnectionInterface
from reade.core.models import DB_METADATA_REGISTRY, DbMetadata
from reade.sql import RenderedQuery, render_template

_SNAPSHOT_PATH = (
    Path(__file__).resolve().parent.parent / "snapshots" / "public_api.json"
)

_REGEN_COMMAND = "uv run python tests/unit/test_public_api.py"

_DRIFT_MESSAGE = (
    "Public API pins differ from tests/snapshots/public_api.json. "
    "An API contract change requires a design-review note in the PR. "
    f"If the change is intended, regenerate with '{_REGEN_COMMAND}' "
    "and review the snapshot diff."
)

# Class-creation machinery that is not API contract. Everything else that
# a class body defines — including generated dunders — is pinned.
_MACHINERY_DUNDERS = frozenset(
    {
        "__abstractmethods__",
        "__annotations__",
        "__class_getitem__",
        "__dataclass_fields__",
        "__dataclass_params__",
        "__dict__",
        "__doc__",
        "__firstlineno__",
        "__init_subclass__",
        "__module__",
        "__non_callable_proto_members__",
        "__orig_bases__",
        "__parameters__",
        "__protocol_attrs__",
        "__qualname__",
        "__slots__",
        "__static_attributes__",
        "__subclasshook__",
        "__type_params__",
        "__weakref__",
    }
)


def _is_dunder(name: str) -> bool:
    return name.startswith("__") and name.endswith("__") and len(name) > 4


def _stable_repr(value: Any) -> str:
    """Render a value deterministically (hash order and ids removed)."""
    if isinstance(value, frozenset | set):
        return "{" + ", ".join(sorted(_stable_repr(item) for item in value)) + "}"
    if isinstance(value, Mapping):
        items = sorted((_stable_repr(k), _stable_repr(v)) for k, v in value.items())
        return "{" + ", ".join(f"{k}: {v}" for k, v in items) + "}"
    if isinstance(value, list):
        return "[" + ", ".join(_stable_repr(item) for item in value) + "]"
    if isinstance(value, tuple):
        return "(" + ", ".join(_stable_repr(item) for item in value) + ")"
    rendered = repr(value)
    if " at 0x" in rendered:
        return f"<{type(value).__qualname__}>"
    return rendered


_LITERAL_DEFAULT_TYPES = (type(None), bool, int, float, str, Enum)


class _StableDefault:
    """Stands in for a parameter default whose repr embeds runtime state."""

    def __init__(self, original: Any) -> None:
        self._type_name = type(original).__qualname__

    def __repr__(self) -> str:
        return f"<{self._type_name}>"


def _pin_signature(func: Any) -> str:
    """Render a signature with non-literal defaults reduced to type names."""
    signature = inspect.signature(func)
    parameters = [
        parameter
        if parameter.default is inspect.Parameter.empty
        or isinstance(parameter.default, _LITERAL_DEFAULT_TYPES)
        else parameter.replace(default=_StableDefault(parameter.default))
        for parameter in signature.parameters.values()
    ]
    return str(signature.replace(parameters=parameters))


def _pin_members(cls: type) -> dict[str, str]:
    members: dict[str, str] = {}
    for name, attr in vars(cls).items():
        # Single-underscore names are internal — except abstract members,
        # which are the extender's contract on a public ABC.
        if (
            name.startswith("_")
            and not _is_dunder(name)
            and not getattr(attr, "__isabstractmethod__", False)
        ):
            continue
        if name in _MACHINERY_DUNDERS:
            continue
        if isinstance(attr, property):
            members[name] = (
                f"property{_pin_signature(attr.fget)}" if attr.fget else "property"
            )
        elif isinstance(attr, classmethod | staticmethod):
            members[name] = _pin_signature(attr.__func__)
        elif callable(attr):
            members[name] = _pin_signature(attr)
        else:
            members[name] = _stable_repr(attr)
    return dict(sorted(members.items()))


def _pin_annotations(cls: type) -> dict[str, str]:
    annotations = {
        name: str(annotation)
        for name, annotation in inspect.get_annotations(cls).items()
        if not name.startswith("_")
    }
    return dict(sorted(annotations.items()))


def _pin_model(cls: type[BaseModel]) -> dict[str, Any]:
    """Pin a pydantic model: fields ride the synthesized signature.

    A generic body walk is deliberately avoided — pydantic's internals
    move between releases (``model_fields`` location, ``__pydantic_*``
    attributes), while the synthesized ``__signature__`` is the stable,
    complete field contract (names, types, defaults).
    """
    class_vars = {
        name: _stable_repr(getattr(cls, name))
        for name, annotation in inspect.get_annotations(cls).items()
        if not name.startswith("_") and "ClassVar" in str(annotation)
    }
    return {
        "class_vars": dict(sorted(class_vars.items())),
        "model_config": _stable_repr(dict(cls.model_config)),
        "signature": _pin_signature(cls),
    }


def _pin_class(cls: type) -> dict[str, Any]:
    pin: dict[str, Any] = {
        "bases": [f"{base.__module__}.{base.__qualname__}" for base in cls.__bases__],
    }
    if issubclass(cls, Enum):
        pin["members"] = {member.name: member.value for member in cls}
    elif issubclass(cls, BaseModel):
        pin.update(_pin_model(cls))
    else:
        members = _pin_members(cls)
        annotations = _pin_annotations(cls)
        if members:
            pin["members"] = members
        if annotations:
            pin["annotations"] = annotations
    return pin


def _pin(obj: Any) -> Any:
    if inspect.isclass(obj):
        return _pin_class(obj)
    if callable(obj):
        return _pin_signature(obj)
    return _stable_repr(obj)


def _direct_subpackages(package: ModuleType) -> list[str]:
    prefix = package.__name__ + "."
    return sorted(
        info.name
        for info in pkgutil.iter_modules(package.__path__, prefix=prefix)
        if info.ispkg
    )


def _mandatory_packages() -> list[str]:
    """The packages whose ``__all__`` defines the public surface.

    Discovered structurally — every direct subpackage of ``reade`` except
    ``core``, plus every direct subpackage of ``reade.core`` — so a
    future module joins the mandatory set by existing, not by opting in.
    """
    feature = [n for n in _direct_subpackages(reade) if n != "reade.core"]
    return sorted([*feature, *_direct_subpackages(reade.core)])


def build_public_api_pins() -> dict[str, Any]:
    """Build the pin map for every exported public symbol.

    The single builder both the snapshot test and the regen entry point
    call — one code path constructs the pins.

    Raises:
        AssertionError: If a mandatory package declares no ``__all__``.
    """
    pins: dict[str, Any] = {}
    for package_name in _mandatory_packages():
        module = importlib.import_module(package_name)
        exported: list[str] | None = getattr(module, "__all__", None)
        assert exported is not None, (
            f"{package_name} declares no __all__ — the public-surface rule "
            "requires one on every public package"
        )
        for symbol_name in exported:
            pins[f"{package_name}.{symbol_name}"] = _pin(getattr(module, symbol_name))
    return pins


def test_package_is_importable() -> None:
    assert reade.__name__ == "reade"


def test_protocol_interfaces_are_importable() -> None:
    assert ConfigLoader is not None
    assert ConnectionInterface is not None


def test_module_errors_derive_from_reade_error() -> None:
    module_errors = (
        ConfigError,
        DataIoError,
        DbError,
        DqError,
        RuleError,
        SqlError,
    )
    assert all(issubclass(error, ReadeError) for error in module_errors)


def test_not_connected_error_derives_from_db_error() -> None:
    assert issubclass(NotConnectedError, DbError)


def test_db_types_cover_exactly_the_mvp_databases() -> None:
    assert set(DbType) == {DbType.SQLITE, DbType.MYSQL, DbType.POSTGRESQL}


def test_file_type_values_are_dotted_extensions() -> None:
    assert all(file_type.value.startswith(".") for file_type in FileType)


def test_sql_render_surface_is_importable() -> None:
    assert RenderedQuery is not None
    assert callable(render_template)


def test_metadata_registry_covers_every_db_type() -> None:
    assert set(DB_METADATA_REGISTRY) == set(DbType)
    assert all(
        isinstance(metadata, DbMetadata) for metadata in DB_METADATA_REGISTRY.values()
    )


def test_root_namespaces_export_nothing() -> None:
    for module in (reade, reade.core):
        public = [
            name
            for name, value in vars(module).items()
            if not name.startswith("_") and not inspect.ismodule(value)
        ]
        assert public == [], (
            f"{module.__name__} exports public names {public} — the root "
            "namespaces are deliberately empty; re-exporting there is a "
            "design review, not a convenience"
        )
        assert not hasattr(module, "__all__")


def test_public_surface_matches_snapshot() -> None:
    actual = build_public_api_pins()

    assert _SNAPSHOT_PATH.exists(), (
        f"{_SNAPSHOT_PATH} is missing — generate it with "
        f"'{_REGEN_COMMAND}' and commit it"
    )
    expected = json.loads(_SNAPSHOT_PATH.read_text(encoding="utf-8"))

    assert actual == expected, _DRIFT_MESSAGE


if __name__ == "__main__":
    _SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    _SNAPSHOT_PATH.write_text(
        json.dumps(build_public_api_pins(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
