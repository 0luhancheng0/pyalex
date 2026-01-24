"""Utility commands for PyAlex CLI."""

import json
import sys
from importlib import import_module
from io import StringIO
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
    ids: Annotated[
        str | None,
        typer.Argument(
            help="OpenAlex IDs (comma-separated). If not provided, reads from stdin."
        ),
    ] = None,
    jsonl_flag: Annotated[
        bool, typer.Option("--jsonl", help="Output JSON Lines to stdout")
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
            help=(
                "Flatten nested fields using pandas.json_normalize before "
                "emitting results"
            ),
        ),
    ] = False,
):
    """Retrieve entities by their OpenAlex IDs from cli or stdin."""

    try:
        effective_jsonl_path, effective_parquet_path = validate_output_format_options(
            jsonl_flag, jsonl_path, parquet_path
        )
        
        if ids:
            parsed_ids = [id.strip() for id in ids.split(",")]
        else:
            payload = sys.stdin.read()
            try:
                parsed_ids = _parse_ids_from_json_input(payload)
            except ValueError as exc:
                typer.echo(f"Error: {exc}", err=True)
                raise typer.Exit(1) from None

        cleaned_ids = _clean_ids(parsed_ids)
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
            jsonl_path=effective_jsonl_path,
            parquet_path=effective_parquet_path,
            normalize=normalize,
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
            help="Path to the JSON/JSONL or Parquet file to display "
            "(if not provided, reads from stdin)"
        ),
    ] = None,
):
    """
    Display a JSON/JSONL or Parquet file containing OpenAlex data in table format.

    Takes a JSON, JSON Lines, or Parquet file as input and displays it in a formatted
    table. Can read JSON or JSON Lines from a file or from stdin if no file is
    provided.

    Examples:
      pyalex show results.json
      pyalex show results.jsonl
      pyalex show results.parquet
      cat results.json | pyalex show
      cat results.jsonl | pyalex show
    """
    def convert_numpy_types(obj):
        """Recursively convert numpy scalars and arrays to Python types."""

        import numpy as np

        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, dict):
            return {k: convert_numpy_types(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [convert_numpy_types(item) for item in obj]
        return obj

    try:
        # Determine the input format
        is_parquet = False
        is_jsonl = False
        if file_path and file_path.lower().endswith(".parquet"):
            is_parquet = True
        elif file_path and (
            file_path.lower().endswith(".jsonl")
            or file_path.lower().endswith(".ndjson")
        ):
            is_jsonl = True

        # Read data
        if is_parquet:
            # Read parquet file
            try:
                import pandas as pd

                df = pd.read_parquet(file_path)
                data = convert_numpy_types(df.to_dict("records"))

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
            try:
                with open(file_path) as f:
                    if is_jsonl:
                        import pandas as pd

                        df = pd.read_json(f, lines=True)
                        data = convert_numpy_types(df.to_dict("records"))
                    else:
                        data = json.load(f)
            except FileNotFoundError:
                typer.echo(f"Error: File '{file_path}' not found", err=True)
                raise typer.Exit(1) from None
            except json.JSONDecodeError as e:
                typer.echo(
                    f"Error: Invalid JSON content in file '{file_path}': {e}",
                    err=True,
                )
                raise typer.Exit(1) from None
            except ValueError as e:
                typer.echo(
                    f"Error: Failed to read JSON Lines file '{file_path}': {e}",
                    err=True,
                )
                raise typer.Exit(1) from None
        else:
            # Read from stdin (JSON or JSON Lines)
            input_data = sys.stdin.read().strip()
            if not input_data:
                typer.echo("Error: No input provided", err=True)
                raise typer.Exit(1)

            try:
                data = json.loads(input_data)
            except json.JSONDecodeError as e:
                # Attempt to parse as JSON Lines if JSON parsing fails
                try:
                    import pandas as pd

                    df = pd.read_json(StringIO(input_data), lines=True)
                    data = convert_numpy_types(df.to_dict("records"))
                except ValueError:
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
