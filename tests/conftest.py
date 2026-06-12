"""Shared test fixtures."""

from pathlib import Path

import pytest


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
