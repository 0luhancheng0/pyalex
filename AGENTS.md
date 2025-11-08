# Repository Guidelines


IF YOU CANT FIND SOME COMMAND IT MAY BE INSTALLED IN THE LOCAL VIRTUAL ENVIRONMENT TRY PREFIX THE COMMAND WITH `uv run`

## Coding Principles 

- Prioritise simplicity over comprehensiveness
- Try reduce the amount of conditional branching, always prioritise vectorised operations especially when you dealing with pandas dataframe
- If something can be done using existing methods for library, do not rewrite them on your own

## Project Structure & Module Organization
Core Python package lives in `pyalex/`, with high-level CLI entry points in `cli.py` and subcommands under `pyalex/cli/`. HTTP orchestration and retry helpers live in `pyalex/client/` and `pyalex/core/`, while entity-specific wrappers sit under `pyalex/entities/`. Shared utilities (logging, type detection, batching) are in `pyalex/utils.py` and `pyalex/logger.py`. End-to-end usage samples live in `pyalex/examples/`. Tests mirror this layout in `tests/` with `test_cli.py`, `test_async_retry.py`, and `test_pyalex.py`. Packaging, dependency, and lint settings are defined in `pyproject.toml`, with pinned sync environments tracked by `uv.lock`.

## Build, Test, and Development Commands
Install editable dependencies (including test and lint extras) with `python -m pip install -e ".[test,lint]"`; `uv sync --all-extras` is also supported for locked environments. Run the CLI locally via `python -m pyalex works --limit 5` or the installed `pyalex` console script. Lint and format in one sweep with `ruff check --fix pyalex tests` followed by `ruff format pyalex tests`. Generate a source distribution when needed using `python -m build`.

## Coding Style & Naming Conventions
Use 4-space indentation, type hints for new public functions, and Google-style docstrings to match existing modules. Modules and functions should stay snake_case, classes PascalCase, and CLI options lowercase with hyphenated names. Keep imports sorted as single lines (enforced by Ruff’s isort settings) and rely on `pyproject.toml` defaults instead of ad-hoc configuration. Prefer Rich-powered logging categories already defined in `pyalex/logger.py` when adding debug output.

## Testing Guidelines
The suite runs on `pytest` with warnings treated as errors (see `[tool.pytest.ini_options]`). Place new tests beside related modules using the `test_*.py` naming pattern and leverage `pytest.mark.asyncio` for async flows. Run all tests with `pytest`, narrow focus via `pytest tests/test_cli.py -k works`, and parallelize when helpful using `pytest -n auto`. Add regression cases whenever touching HTTP retry logic, CLI parsing, or async batching.

## Commit & Pull Request Guidelines
Recent history favors short imperative summaries (for example, `bug fix`, `update --json option`); keep that tone but aim for clarity under 50 characters. Reference related issues in the body and note any CLI or API changes. Before opening a PR, run lint + tests, include reproduction or demo commands, update docs when behavior shifts, and attach screenshots for CLI output tweaks that affect formatting. Mark PRs as draft until automated checks pass or known gaps are documented, and confirm that pre-commit hooks (`pre-commit run --all-files`) are clean.


