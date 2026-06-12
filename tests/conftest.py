"""Shared test fixtures."""

import os
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolate_reade_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip READE__* variables so a developer's shell cannot poison tests."""
    for name in [var for var in os.environ if var.startswith("READE__")]:
        monkeypatch.delenv(name)


@pytest.fixture
def valid_yaml_file(tmp_path: Path) -> Path:
    """A YAML config file with nested mapping content."""
    file_path = tmp_path / "valid.yaml"
    file_path.write_text("database:\n  host: localhost\n  port: 5432\n")
    return file_path


@pytest.fixture
def empty_yaml_file(tmp_path: Path) -> Path:
    """An empty YAML file."""
    file_path = tmp_path / "empty.yaml"
    file_path.write_text("")
    return file_path


@pytest.fixture
def invalid_yaml_file(tmp_path: Path) -> Path:
    """A YAML file whose content fails to parse."""
    file_path = tmp_path / "invalid.yaml"
    file_path.write_text("invalid: yaml: content:\n  - broken")
    return file_path
