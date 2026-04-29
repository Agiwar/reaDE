# ruff: noqa: T201  # Demo script — print() is intentional.
"""Demo: load YAML, JSON, and CSV configs via reaDE's config utility.

Run from the repo root:

    python examples/basic_config_loading.py

Sample configs live next to this script in `sample_configs/`. The demo
resolves them via ``base_path`` so it works regardless of the caller's
current working directory.
"""

from pathlib import Path

from reade.config.utils import get_config_content

SAMPLE_CONFIGS = Path(__file__).parent / "sample_configs"


def main() -> None:
    """Load each sample config and print its parsed contents."""
    db_config = get_config_content("db.yaml", base_path=SAMPLE_CONFIGS)
    app_config = get_config_content("app.json", base_path=SAMPLE_CONFIGS)
    settings = get_config_content("settings.csv", base_path=SAMPLE_CONFIGS)

    print("=== db.yaml (YAML) ===")
    print(f"  type:   {db_config['database']['type']}")
    print(f"  host:   {db_config['database']['host']}")
    print(f"  port:   {db_config['database']['port']}")
    print(f"  name:   {db_config['database']['name']}")

    print("\n=== app.json (JSON) ===")
    print(f"  service: {app_config['service']}")
    print(f"  version: {app_config['version']}")
    print(f"  debug:   {app_config['debug']}")

    print("\n=== settings.csv (CSV) ===")
    for key, value in settings.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
