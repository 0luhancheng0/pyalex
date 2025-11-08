"""Utility commands for PyAlex CLI."""

import json
import sys
from importlib import import_module
from typing import Annotated

import typer
from typer.core import TyperCommand

from pyalex.exceptions import CLIError
from pyalex.exceptions import DataError
from pyalex.exceptions import ValidationError

from ..command_patterns import validate_output_format_options
from ..utils import _async_retrieve_entities
from ..utils import _clean_ids
from ..utils import _handle_cli_exception
from ..utils import _output_results
from ..utils import _parse_ids_from_json_input


class StdinSentinelCommand(TyperCommand):
    """Command class that injects stdin sentinels for specified options."""

    _stdin_options: dict[str, str] = {}

    def parse_args(self, ctx, args):  # type: ignore[override]
        processed: list[str] = []
        i = 0
        while i < len(args):
            arg = args[i]
            processed.append(arg)

            sentinel = self._stdin_options.get(arg)
            if sentinel:
                next_index = i + 1
                if next_index >= len(args) or args[next_index].startswith("-"):
                    processed.append(sentinel)

            i += 1

        return super().parse_args(ctx, processed)

_ENTITY_PREFIX_MAP: dict[str, str] = {
    "SF": "Subfields",
    "FI": "Fields",
    "W": "Works",
    "A": "Authors",
    "I": "Institutions",
    "S": "Sources",
    "F": "Funders",
    "P": "Publishers",
    "T": "Topics",
    "D": "Domains",
    "K": "Keywords",
}


def _load_entity_class_from_prefix(openalex_id: str) -> tuple[type, str]:
    """Resolve the entity class based on an OpenAlex ID prefix."""

    identifier = openalex_id.strip().upper()
    prefix = None

    # Check two-character prefixes first (e.g., SF for subfields)
    if len(identifier) >= 2:
        candidate = identifier[:2]
        if candidate in _ENTITY_PREFIX_MAP:
            prefix = candidate

    if prefix is None and identifier:
        candidate = identifier[0]
        if candidate in _ENTITY_PREFIX_MAP:
            prefix = candidate

    if prefix is None:
        raise ValueError(f"Unknown ID prefix in '{openalex_id}'")

    class_name = _ENTITY_PREFIX_MAP[prefix]

    try:
        module = import_module("pyalex")
        entity_class = getattr(module, class_name)
    except AttributeError as exc:  # pragma: no cover - defensive
        raise ValueError(
            f"Could not determine entity type for '{openalex_id}'"
        ) from exc

    return entity_class, class_name


def from_ids(
    json_flag: Annotated[
        bool, typer.Option("--json", help="Output JSON to stdout")
    ] = False,
    json_path: Annotated[
        str | None,
        typer.Option(
            "--json-file", help="Save results to JSON file at specified path"
        ),
    ] = None,
    parquet_path: Annotated[
        str | None,
        typer.Option(
            "--parquet-file",
            help="Save results to Parquet file at specified path",
        ),
    ] = None,
):
    """Retrieve entities by their OpenAlex IDs from stdin."""

    try:
        effective_json_path, effective_parquet_path = validate_output_format_options(
            json_flag, json_path, parquet_path
        )

        payload = sys.stdin.read()
        try:
            ids = _parse_ids_from_json_input(payload)
        except ValueError as exc:
            typer.echo(f"Error: {exc}", err=True)
            raise typer.Exit(1) from None

        cleaned_ids = _clean_ids(ids)
        if not cleaned_ids:
            typer.echo("Error: No IDs found in input", err=True)
            raise typer.Exit(1)

        first_id = cleaned_ids[0]
        try:
            entity_class, class_name = _load_entity_class_from_prefix(first_id)
        except ValueError as exc:
            typer.echo(f"Error: {exc}", err=True)
            raise typer.Exit(1) from None

        import asyncio

        results = asyncio.run(
            _async_retrieve_entities(entity_class, cleaned_ids, class_name)
        )

        _output_results(
            results,
            json_path=effective_json_path,
            parquet_path=effective_parquet_path,
        )

    except (CLIError, DataError, ValidationError) as exc:
        _handle_cli_exception(exc)
        raise typer.Exit(1) from exc
    except Exception as exc:  # pragma: no cover - unexpected
        _handle_cli_exception(exc)
        raise typer.Exit(1) from exc


def show(
    file_path: Annotated[
        str | None,
        typer.Argument(
            help="Path to the JSON or Parquet file to display "
            "(if not provided, reads from stdin)"
        ),
    ] = None,
):
    """
    Display a JSON or Parquet file containing OpenAlex data in table format.

    Takes a JSON or Parquet file as input and displays it in a formatted table.
    Can read JSON from a file or from stdin if no file is provided.

    Examples:
      pyalex show results.json
      pyalex show results.parquet
      cat results.json | pyalex show
    """
    try:
        # Determine if input is parquet or JSON
        is_parquet = False
        if file_path and file_path.lower().endswith(".parquet"):
            is_parquet = True

        # Read data
        if is_parquet:
            # Read parquet file
            try:
                import pandas as pd

                df = pd.read_parquet(file_path)
                # Convert to list of dicts for consistent processing
                # Use orient='records' which handles nested structures better
                data = df.to_dict("records")

                # Convert any numpy types to native Python types for JSON serialization
                def convert_numpy_types(obj):
                    """Recursively convert numpy types to Python native types."""
                    import numpy as np

                    if isinstance(obj, np.integer):
                        return int(obj)
                    elif isinstance(obj, np.floating):
                        return float(obj)
                    elif isinstance(obj, np.ndarray):
                        return obj.tolist()
                    elif isinstance(obj, dict):
                        return {k: convert_numpy_types(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [convert_numpy_types(item) for item in obj]
                    else:
                        return obj

                # Apply conversion to all data
                data = convert_numpy_types(data)

            except FileNotFoundError:
                typer.echo(f"Error: File '{file_path}' not found", err=True)
                raise typer.Exit(1) from None
            except Exception as e:
                typer.echo(
                    f"Error: Failed to read Parquet file '{file_path}': {e}",
                    err=True,
                )
                raise typer.Exit(1) from None
        elif file_path:
            # Read JSON file
            try:
                with open(file_path) as f:
                    data = json.load(f)
            except FileNotFoundError:
                typer.echo(f"Error: File '{file_path}' not found", err=True)
                raise typer.Exit(1) from None
            except json.JSONDecodeError as e:
                typer.echo(f"Error: Invalid JSON in file '{file_path}': {e}", err=True)
                raise typer.Exit(1) from None
        else:
            # Read from stdin (JSON only)
            input_data = sys.stdin.read().strip()
            if not input_data:
                typer.echo("Error: No input provided", err=True)
                raise typer.Exit(1)

            try:
                data = json.loads(input_data)
            except json.JSONDecodeError as e:
                typer.echo(f"Error: Invalid JSON input: {e}", err=True)
                raise typer.Exit(1) from None

        # Display the data (table output only)
        if isinstance(data, dict):
            # Check if this is a grouped result (contains group_by field)
            if "group_by" in data and isinstance(data["group_by"], list):
                # This is grouped data from --group-by option
                _output_results(data["group_by"], grouped=True)
            else:
                # Single entity
                _output_results(data, single=True)
        elif isinstance(data, list):
            # Check if this is a list of grouped items (key, key_display_name, count)
            if (
                data
                and len(data) > 0
                and isinstance(data[0], dict)
                and all(key in data[0] for key in ["key", "key_display_name", "count"])
                and len(data[0]) == 3
            ):
                # This is grouped data
                _output_results(data, grouped=True)
            else:
                # List of entities
                _output_results(data)
        else:
            typer.echo("Error: Input must be a JSON object or array", err=True)
            raise typer.Exit(1)

    except (CLIError, DataError) as e:
        _handle_cli_exception(e)
        raise typer.Exit(1) from e
    except Exception as e:
        _handle_cli_exception(e)
        raise typer.Exit(1) from e


def create_utils_commands(app):
    """Register utility commands with the app."""
    app.command()(from_ids)
    app.command()(show)
