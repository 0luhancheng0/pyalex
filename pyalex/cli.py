"""
PyAlex CLI Module - Refactored to use modular structure.

This module now imports the main CLI application from the cli submodule,
which contains a properly organized structure with separate files for
different command types and utilities.
"""

# Import the main CLI app from the modular structure
from .cli import app

# This is the main entry point for the CLI
if __name__ == "__main__":
    app()
