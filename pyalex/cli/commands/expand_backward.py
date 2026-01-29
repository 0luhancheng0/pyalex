"""
Expand backward command for PyAlex CLI.

This command extracts referenced works (backward citations) from a JSONL file of Works and fetches their details.
"""

import asyncio
import json
import sys
from typing import Annotated

import typer

from pyalex import Works
from ..utils import _async_retrieve_entities
from ..utils import _handle_cli_exception
from ..utils import _output_results
from ..command_patterns import validate_output_format_options


def expand_backward(
    input_jsonl: Annotated[
        str,
        typer.Option(
            "--input-jsonl",
            "-i",
            help="Path to input JSONL file containing Works",
        ),
    ],
    jsonl_flag: Annotated[
        bool,
        typer.Option(
            "--jsonl",
            help="Output JSON Lines to stdout",
        ),
    ] = False,
    jsonl_path: Annotated[
        str | None,
        typer.Option(
            "--jsonl-file",
            help="Save results to JSON Lines file at specified path",
        ),
    ] = None,
    parquet_path: Annotated[
        str | None,
        typer.Option(
            "--parquet-file",
            help="Save results to Parquet file at specified path",
        ),
    ] = None,
    normalize: Annotated[
        bool,
        typer.Option(
            "--normalize",
            help="Flatten nested fields using pandas.json_normalize before emitting results",
        ),
    ] = False,
):
    """
    Extract and fetch backward citations (referenced works) from a JSONL file of Works.

    Reads a JSONL file containing OpenAlex Works, extracts all IDs from the
    'referenced_works' field, deduplicates them, and fetches their full details.
    """
    try:
        effective_jsonl_path, effective_parquet_path = validate_output_format_options(
            jsonl_flag, jsonl_path, parquet_path
        )

        referenced_ids = set()

        # Read input file and collect IDs
        try:
            with open(input_jsonl, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        # referenced_works is a list of URLs (strings)
                        refs = data.get("referenced_works", [])
                        if refs:
                            for ref in refs:
                                # Clean ID: remove https://openalex.org/ if present
                                clean_id = ref.replace("https://openalex.org/", "")
                                referenced_ids.add(clean_id)
                    except json.JSONDecodeError:
                        continue
        except FileNotFoundError:
            typer.echo(f"Error: Input file '{input_jsonl}' not found.", err=True)
            raise typer.Exit(1) from None

        if not referenced_ids:
            typer.echo("No referenced works found in input file.", err=True)
            return

        sorted_ids = sorted(list(referenced_ids))

        # Fetch entities
        results = asyncio.run(
            _async_retrieve_entities(Works, sorted_ids, "Works")
        )

        # Output results
        _output_results(
            results,
            jsonl_path=effective_jsonl_path,
            parquet_path=effective_parquet_path,
            normalize=normalize,
        )

    except Exception as e:
        _handle_cli_exception(e)


def create_expand_backward_command(app):
    """Create and register the expand-backward command."""
    app.command(name="expand-backward", rich_help_panel="Utility Commands")(expand_backward)