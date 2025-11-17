# AGENTS.md

## Build/Lint/Test Commands
- Build: `uv build`
- Lint: `uv run ruff check .`
- Format: `uv run ruff format .`
- Test: `uv run pytest`
- Single test: `uv run pytest path/to/test.py::TestClass::test_method`

## Code Style Guidelines
- Use `uv` for Python environment and dependency management.
- Follow PEP8 for code style.
- Imports: Standard library first, then third-party, then local modules.
- Formatting: Use `ruff format` for consistent formatting.
- Types: Use type hints for function parameters and return values.
- Naming: snake_case for functions/variables, CamelCase for classes, UPPER_CASE for constants.
- Error handling: Use try/except blocks, raise custom exceptions with descriptive messages.
- Docstrings: Use Google-style docstrings for functions and classes.
- Logging: Use `logging` module for debug/info/error messages.
- Security: Avoid hardcoding secrets; use environment variables.
- Testing: Write unit tests with pytest, aim for high coverage.

No Cursor or Copilot rules found.