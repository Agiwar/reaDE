# reaDE

Data Engineering SDK with built-in Data Quality — connect, query,
validate.

This site is the per-symbol API reference for the frozen v0.3.0
surface: 44 pinned symbols across 11 public packages, rendered from
the docstrings that are the contract (docstring-first — behavior
documented there is binding, including which exceptions a method
raises).

Where everything lives:

- [Stability table](stability.md) — every pinned symbol and its
  disposition, cross-checked against the public-API snapshot by a
  committed test.
- [Freeze record](api_freeze.md) — the classification rubric, the
  Sprint 4.1 walk, and the Sprint 4.2 delta.
- [README](https://github.com/Agiwar/reaDE#readme) — installation,
  quick start, configuration, and examples.
- [ARCHITECTURE](https://github.com/Agiwar/reaDE/blob/main/ARCHITECTURE.md)
  — layers, module roles, and the dependency chain.

The reference is built locally: `make docs` writes the site to `site/`
(untracked), or `uv run mkdocs serve` serves it live.
