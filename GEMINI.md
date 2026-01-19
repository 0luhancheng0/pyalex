# ♊ PyAlex Gemini Guidelines

This document serves as a high-level guide for AI agents (like Gemini) working on the **PyAlex** repository. It provides context on the project's purpose, technical stack, structure, and development standards.

## 🚀 Project Overview

**PyAlex** is a modern, asynchronous Python library and CLI for interacting with the [OpenAlex API](https://openalex.org/). It focuses on providing a powerful, type-safe, and efficient way to query scholarly metadata.

### Key Capabilities
- **Async-First Architecture**: Built on `httpx` and `asyncio`.
- **Comprehensive CLI**: Rich command-line interface powered by `Typer`.
- **MCP Server**: Exposes OpenAlex search capabilities as tools for Model Context Protocol agents.
- **Data Engineering**: Specialized tools for taxonomy generation, merging, and pruning.

---

## 🛠️ Technical Stack

- **Core**: Python 3.10+
- **HTTP/Networking**: [httpx](https://www.python-httpx.org/) (with HTTP/2 support)
- **CLI Framework**: [Typer](https://typer.tiangolo.com/)
- **Data Handling**: [Pydantic](https://docs.pydantic.dev/) for models, [Pandas](https://pandas.pydata.org/) for dataframes
- **Package Management**: [pixi](https://pixi.sh/) / [uv](https://github.com/astral-sh/uv)
- **Quality Control**: [Ruff](https://beta.ruff.rs/docs/) (linting/formatting), [pytest](https://docs.pytest.org/) (testing)

---

## 📂 Project Structure

- `pyalex/`: Core library source code.
    - `api.py`: Main API client entry point.
    - `entities/`: Data models and entity-specific logic (Works, Authors, etc.).
    - `client/`: Base client implementations.
    - `cli/`: Sub-commands for the `pyalex` CLI.
    - `mcp/`: Model Context Protocol server implementation.
    - `agents/`: Specialized agent-like scripts (e.g., taxonomy landscaping).
- `examples/`: Comprehensive usage examples for API and CLI.
- `docs/`: Additional documentation for specific features (e.g., embeddings).
- `tests/`: Unit and integration tests.

---

## 📝 Strategic Guidelines

### Coding Principles
- **Prefer Simplicity**: Avoid over-engineering. Stick to existing patterns.
- **Asynchronous Logic**: Always use `async/await` for networking and I/O.
- **Type Safety**: Use type hints for all new public functions and classes.
- **Vectorization**: Prioritize vectorized operations when working with DataFrames; avoid explicit loops.

### Standards
- **Indent**: 4 spaces.
- **Style**: Google-style docstrings.
- **Formatting**: Enforced by Ruff. Run `ruff format` before submitting.
- **Logging**: Use the pre-defined categories in `pyalex/logger.py`.

### Sibling Documentation
- [README.md](file:///Users/luhancheng/pyalex/README.md): Installation and quick start.
- [AGENTS.md](file:///Users/luhancheng/pyalex/AGENTS.md): Repository-specific rules and "don't touch" warnings.
- [PLAN.md](file:///Users/luhancheng/pyalex/PLAN.md): Current development roadmap.

---

## ⚠️ Important Reminders

- **Don't Fix What's Working**: Avoid refactoring stable code unless explicitly asked to fix a bug in that specific area.
- **Environment**: If a command is missing, try prefixing with `pixi run`.
- **Existing Tools**: Always check if a capability exists in the library before rewriting it.
