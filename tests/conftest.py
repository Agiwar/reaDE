"""Shared test fixtures."""

from pathlib import Path

import pytest


@pytest.fixture
def tmp_config_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for config files."""
    return tmp_path


@pytest.fixture
def valid_yaml_file(tmp_config_dir: Path) -> Path:
    """Create a valid YAML config file."""
    file_path = tmp_config_dir / "valid.yaml"
    file_path.write_text("database:\n  host: localhost\n  port: 5432\n")
    return file_path


@pytest.fixture
def empty_yaml_file(tmp_config_dir: Path) -> Path:
    """Create an empty YAML file."""
    file_path = tmp_config_dir / "empty.yaml"
    file_path.write_text("")
    return file_path


@pytest.fixture
def invalid_yaml_file(tmp_config_dir: Path) -> Path:
    """Create an invalid YAML file."""
    file_path = tmp_config_dir / "invalid.yaml"
    file_path.write_text("invalid: yaml: content:\n  - broken")
    return file_path
