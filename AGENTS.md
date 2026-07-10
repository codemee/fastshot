# Project Instructions

## Python Environment

- Manage the Python environment with `uv`.
- Use `uv sync` to install dependencies from `pyproject.toml` and `uv.lock`.
- Use `uv add <package>` or `uv add --dev <package>` to add dependencies.
- Run Python tools through `uv run`, for example `uv run python`, `uv run pytest`, or project scripts.
- Do not use `pip install` directly unless `uv` cannot support the required operation.

## Development Notes

- Read `README.md`, `docs/architecture.md`, and `docs/cross-platform.md` before changing capture, hotkey, or platform-specific behavior.
- Keep dependency metadata in `pyproject.toml`.
- Commit `uv.lock` when it is present so dependency resolution is reproducible.
- Prefer small, focused changes that match the existing project structure.
