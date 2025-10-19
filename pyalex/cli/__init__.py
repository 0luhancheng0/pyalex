"""
CLI submodule for PyAlex command-line interface.

This module is organized into separate files for better maintainability:
- __init__.py: Main CLI app and imports
- batch.py: Batch processing utilities and configurations
- utils.py: Common utilities for CLI operations
- commands/: Individual entity command implementations
"""

from .main import app

__all__ = ["app"]
