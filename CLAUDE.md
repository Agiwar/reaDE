# Claude Code Instructions for reaDE

## Response Philosophy

When assisting with this project, Claude should:

1. **Apply Industry Best Practices First**
   - Always provide solutions based on established conventions, standards, and common patterns
   - Reference authoritative sources (PEPs, Conventional Commits, official docs) when relevant
   - Don't just give answers - explain WHY it's the recommended approach

2. **Reason Before Responding**
   - Think through implications and trade-offs before suggesting solutions
   - Consider edge cases and potential issues proactively
   - If multiple valid approaches exist, present them with pros/cons

3. **Be Proactively Smart**
   - Anticipate follow-up questions and address them preemptively
   - Point out potential issues or improvements the user hasn't asked about
   - Validate assumptions rather than accepting them blindly

4. **Prioritize Correctness Over Speed**
   - Take time to research/verify rather than guessing
   - If uncertain, say so and investigate first
   - Never provide placeholder or incomplete solutions

## Project Context

- **Type**: Python SDK for data engineering (ETL, replication, transformations)
- **Architecture**: Interface → Implementation → Factory → Utils pattern
- **Python Version**: 3.13+
- **Package Manager**: uv (not pip)
- **Linting/Formatting**: Ruff (replaces black, isort, flake8)
- **Type Checking**: Mypy with strict mode
- **Testing**: Pytest with coverage
- **Docstring Style**: Google-style

## Git Conventions

- **Branch Prefixes**: `feat/`, `fix/`, `chore/`, `docs/`, `refactor/`, `test/`, `ci/`
- **Commit Style**: Conventional Commits (`type: description`)
- **Workflow**: main ← feature branches (no dev/release branches for solo project)

## Code Standards

- Type hints required on all public functions
- Google-style docstrings for public APIs
- Keep functions small and focused (single responsibility)
- Prefer composition over inheritance
- Use Protocol classes for interfaces (not ABC when possible)
- Avoid premature optimization - clarity first

## When Making Suggestions

- Check if similar patterns exist in the codebase first
- Follow existing code style and conventions
- Prefer editing existing files over creating new ones
- Don't add features beyond what's requested
- Run linting/type checks after changes when relevant
