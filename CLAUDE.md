# Claude Code Instructions for reaDE

## Response Philosophy

When assisting with this project, Claude should:

1. **No Flattery or Emotional Validation**
   - No empty praise ("Great idea!", "You're absolutely right!")
   - No emotional support or encouragement
   - Strictly correct mistakes when they occur
   - Be direct and factual - if the idea is wrong, say so clearly

2. **Apply Industry Best Practices First**
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

- **Type**: Python SDK providing unified interfaces for DB connections, config loading, and validation
- **Purpose**: Eliminate boilerplate that every DE rewrites (DRY principle)
- **Architecture**: Interface (Protocol) → Base (ABC) → Implementation → Factory pattern
- **Python Version**: 3.12+
- **Package Manager**: uv (not pip)
- **Linting/Formatting**: Ruff 0.6+ (replaces black, isort, flake8)
- **Type Checking**: Mypy with strict mode
- **Testing**: Pytest with coverage
- **Docstring Style**: Google-style

## MVP Scope

- **Core DBs**: PostgreSQL, MySQL, SQLite (zero-setup for tests)
- **Optional**: Trino (analytics engine)
- **Not in MVP**: Oracle, DB2, ClickHouse, Snowflake, Spark, dbt, orchestration

## Git Conventions

- **Branch Prefixes**: `feat/`, `fix/`, `chore/`, `docs/`, `refactor/`, `test/`, `ci/`
- **Commit Style**: Conventional Commits (`type: description`)
- **Workflow**: main ← feature branches (no dev/release branches for solo project)
- **Author Identity**: Jeffrey <agiwar791005@gmail.com> (real name and email)
- **Commit Signing**: SSH signing enabled for verified commits on GitHub
- **Commit Messages**:
  - Do NOT add "Generated with Claude Code" or "Co-Authored-By: Claude" footers
  - Keep messages clean and concise (industry standard)
  - Include high-level summary of what/why changed
  - Avoid excessive detail (no file listings, known patterns, obvious implementation details)
- **PR Workflow**:
  - Implement code + tests together (atomic commits)
  - Push to feature branch → Create PR → Squash merge to main
  - Delete remote and local branch after merge
  - Squash merge keeps main history clean (no need for perfect commits during dev)

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
