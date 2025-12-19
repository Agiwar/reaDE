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


# CSV fixtures
@pytest.fixture
def valid_csv_file(tmp_config_dir: Path) -> Path:
    """Create a valid CSV config file with key-value pairs."""
    file_path = tmp_config_dir / "valid.csv"
    file_path.write_text("host,localhost\nport,5432\n")
    return file_path


@pytest.fixture
def empty_csv_file(tmp_config_dir: Path) -> Path:
    """Create an empty CSV file."""
    file_path = tmp_config_dir / "empty.csv"
    file_path.write_text("")
    return file_path


@pytest.fixture
def keys_only_csv_file(tmp_config_dir: Path) -> Path:
    """Create a CSV file with only keys (no values)."""
    file_path = tmp_config_dir / "keys_only.csv"
    file_path.write_text("host\nport\n")
    return file_path


@pytest.fixture
def extra_columns_csv_file(tmp_config_dir: Path) -> Path:
    """Create a CSV file with extra columns beyond key-value."""
    file_path = tmp_config_dir / "extra.csv"
    file_path.write_text("host,localhost,extra,columns\nport,5432,ignored\n")
    return file_path


@pytest.fixture
def quoted_csv_file(tmp_config_dir: Path) -> Path:
    """Create a CSV file with quoted values containing commas."""
    file_path = tmp_config_dir / "quoted.csv"
    file_path.write_text('message,"Hello, World"\npath,"/usr/local/bin"\n')
    return file_path


# JSON fixtures
@pytest.fixture
def valid_json_file(tmp_config_dir: Path) -> Path:
    """Create a valid JSON config file."""
    file_path = tmp_config_dir / "valid.json"
    file_path.write_text('{"database": {"host": "localhost", "port": 5432}}')
    return file_path


@pytest.fixture
def empty_json_file(tmp_config_dir: Path) -> Path:
    """Create an empty JSON file."""
    file_path = tmp_config_dir / "empty.json"
    file_path.write_text("")
    return file_path


@pytest.fixture
def invalid_json_file(tmp_config_dir: Path) -> Path:
    """Create an invalid JSON file."""
    file_path = tmp_config_dir / "invalid.json"
    file_path.write_text('{"unclosed": "brace"')
    return file_path
