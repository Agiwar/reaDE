# reaDE Examples

Runnable scripts that demonstrate reaDE's currently functional APIs. Use
these to learn the surface area or to evaluate the project — they are
**not** intended for production use.

## Contents

```
examples/
├── basic_config_loading.py   # Load YAML / JSON / CSV via get_config_content()
└── sample_configs/
    ├── db.yaml               # Database config with ${VAR} placeholders
    ├── app.json              # App service config
    └── settings.csv          # Key-value settings
```

## Running

Install reaDE in editable mode first (see the repo [README](../README.md#installation)),
then run examples from the **repo root**:

```bash
# Load and print the sample configs
python examples/basic_config_loading.py
```

## Notes

- Sample configs use `${VAR}` placeholders for credentials — they are
  illustrative only and contain no real secrets.
- Examples resolve their config paths relative to each script, so they
  work regardless of the caller's current working directory.
- Modules not yet implemented (`sql/`, `data_io/`, `validation/`, `dq/`)
  do not yet have examples; check the repo README for module status.
