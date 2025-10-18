# PyAlex Examples

This directory contains working examples and tutorials for using PyAlex.

## Quick Start

The examples are organized by complexity:

1. **basic_usage.py** - Start here! Simple queries and filters
2. **advanced_filtering.py** - Complex filters and combinations
3. **pagination_examples.py** - Handling large result sets
4. **batch_operations.py** - Processing multiple items efficiently
5. **async_usage.py** - Using async for better performance

## Jupyter Notebooks

- **[getting_started.ipynb](getting_started.ipynb)** - Interactive tutorial
- **[data_analysis.ipynb](data_analysis.ipynb)** - Analyzing research data

## CLI Examples

See [CLI_EXAMPLES.md](CLI_EXAMPLES.md) for command-line usage examples.

## Configuration

All examples can be configured using environment variables. Copy `.env.example` from the root directory:

```bash
cp ../.env.example .env
# Edit .env with your configuration
```

## Running Examples

```bash
# Install PyAlex first
pip install -e ..

# Run an example
python basic_usage.py
```

## Need Help?

- Check the [main README](../README.md)
- See the [migration guide](../ASYNC_ONLY_MIGRATION.md)
- Open an issue on GitHub
