"""
Expand forward command for PyAlex CLI.

This command gets all works that cite the input works (forward citations).
It reads a JSONL file of Works, extracts their IDs, and retrieves works that cite them.
"""

import json
from typing import Annotated

import typer

from pyalex import Works
from ..batch import add_id_list_option_to_command
from ..command_patterns import execute_standard_query
from ..command_patterns import handle_large_id_list_if_needed
from ..command_patterns import validate_output_format_options
from ..utils import _handle_cli_exception
from ..utils import _output_results


def expand_forward(
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
    Extract IDs from a JSONL file of Works and fetch works that cite them (forward citations).

    Reads a JSONL file containing OpenAlex Works, extracts their IDs,
    and queries for works that cite these IDs.
    """
    try:
        effective_jsonl_path, effective_parquet_path = validate_output_format_options(
            jsonl_flag, jsonl_path, parquet_path
        )

        input_ids = set()

        # Read input file and collect IDs
        try:
            with open(input_jsonl, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        work_id = data.get("id")
                        if work_id:
                            # Clean ID: remove https://openalex.org/ if present
                            clean_id = work_id.replace("https://openalex.org/", "")
                            input_ids.add(clean_id)
                    except json.JSONDecodeError:
                        continue
        except FileNotFoundError:
            typer.echo(f"Error: Input file '{input_jsonl}' not found.", err=True)
            raise typer.Exit(1) from None

        if not input_ids:
            typer.echo("No work IDs found in input file.", err=True)
            return

        sorted_ids = sorted(list(input_ids))
        typer.echo(f"Found {len(sorted_ids)} unique input works.", err=True)

        # Build query
        query = Works()

        # Use existing logic to add the "cites" filter
        # This will automatically handle batching if the list is large
        id_string = ",".join(sorted_ids)
        query = add_id_list_option_to_command(query, id_string, "works_cites", Works)

        # Handle large ID lists (batch processing) or execute standard query
        results = handle_large_id_list_if_needed(
            query,
            Works,
            True, # all_results
            None, # limit
            effective_jsonl_path,
            normalize=normalize,
        )

        # If handle_large_id_list_if_needed returns None, it means it wasn't a large list
        # (or at least handled as a large list). We execute standard query.
        # Note: handle_large_id_list_if_needed DOES output results if it runs.
        if results is None:
            results = execute_standard_query(
                query, "Works", all_results=True, limit=None
            )

            # Output results for standard query
            _output_results(
                results,
                jsonl_path=effective_jsonl_path,
                parquet_path=effective_parquet_path,
                normalize=normalize,
            )

    except Exception as e:
        _handle_cli_exception(e)


def create_expand_forward_command(app):
    """Create and register the expand-forward command."""
    app.command(name="expand-forward", rich_help_panel="Utility Commands")(
        expand_forward
    )
