# Installation

## Requirements

- Python 3.8 or higher
- pip or uv package manager

## Install from PyPI

```bash
pip install pyalex
```

## Install from Source

```bash
git clone https://github.com/0luhancheng0/pyalex.git
cd pyalex
pip install -e .
```

## Optional Dependencies

### Development Dependencies

For linting and code formatting:

```bash
pip install pyalex[lint]
```

### Test Dependencies

For running tests:

```bash
pip install pyalex[test]
```

### Documentation Dependencies

For building documentation:

```bash
pip install pyalex[docs]
```

### All Dependencies

Install everything:

```bash
pip install pyalex[lint,test,docs]
```

## Verify Installation

### Check Python API

```python
import pyalex
print(pyalex.__version__)
```

### Check CLI

```bash
pyalex --help
```

You should see the CLI help message with available commands.

## Next Steps

- [Quick Start Guide](quickstart.md) - Get started with basic usage
- [Configuration](configuration.md) - Set up environment variables and API keys
