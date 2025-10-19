"""
Utility commands for PyAlex CLI.
"""

import json
import sys
from typing import Annotated

import typer

from pyalex.exceptions import CLIError
from pyalex.exceptions import DataError
from pyalex.exceptions import ValidationError

from ..utils import _async_retrieve_entities
from ..utils import _clean_ids
from ..utils import _handle_cli_exception
from ..utils import _output_results


def from_ids(
    json_path: Annotated[
        str | None,
        typer.Option("--json", help="Save results to JSON file at specified path"),
    ] = None,
):
    """
    Retrieve entities by their OpenAlex IDs from stdin.

    Expects JSON input containing either:
    - A single entity with an 'id' field
    - A list of entities, each with an 'id' field
    - A list of ID strings

    Examples:
      echo '["W1234567890", "W0987654321"]' | pyalex from-ids
      echo '{"id": "W1234567890"}' | pyalex from-ids --json results.json
      cat work_ids.json | pyalex from-ids
    """
    try:
        # Read JSON from stdin
        input_data = sys.stdin.read().strip()
        if not input_data:
            typer.echo("Error: No input provided", err=True)
            raise typer.Exit(1)

        try:
            data = json.loads(input_data)
        except json.JSONDecodeError as e:
            typer.echo(f"Error: Invalid JSON input: {e}", err=True)
            raise typer.Exit(1) from e

        # Extract IDs from input
        ids = []
        entity_class = None

        if isinstance(data, dict):
            # Single entity object
            if "id" in data:
                ids = [data["id"]]
            else:
                typer.echo("Error: No 'id' field found in input object", err=True)
                raise typer.Exit(1)
        elif isinstance(data, list):
            if not data:
                typer.echo("Error: Empty list provided", err=True)
                raise typer.Exit(1)

            # Check if it's a list of strings (IDs) or objects
            if isinstance(data[0], str):
                # List of ID strings
                ids = data
            elif isinstance(data[0], dict):
                # List of entity objects
                for item in data:
                    if "id" in item:
                        ids.append(item["id"])
                    else:
                        typer.echo("Error: Missing 'id' field in list item", err=True)
                        raise typer.Exit(1)
            else:
                typer.echo("Error: Invalid list format", err=True)
                raise typer.Exit(1)
        else:
            typer.echo("Error: Input must be a JSON object or array", err=True)
            raise typer.Exit(1)

        if not ids:
            typer.echo("Error: No IDs found in input", err=True)
            raise typer.Exit(1)

        # Clean IDs and determine entity type
        cleaned_ids = _clean_ids(ids)

        # Determine entity type from first ID
        first_id = cleaned_ids[0]
        id_prefixes = {
            "W": ("Works", "works"),
            "A": ("Authors", "authors"),
            "I": ("Institutions", "institutions"),
            "S": ("Sources", "sources"),
            "F": ("Funders", "funders"),
            "P": ("Publishers", "publishers"),
            "T": ("Topics", "topics"),
            "D": ("Domains", "domains"),
            "SF": ("Subfields", "subfields"),
            "FI": ("Fields", "fields"),
            "K": ("Keywords", "keywords"),
        }

        # Check for 2-letter prefixes first, then 1-letter
        entity_info = None
        for prefix in ["SF", "FI"]:  # Check 2-letter prefixes first
            if first_id.startswith(prefix):
                entity_info = id_prefixes[prefix]
                break

        if not entity_info:
            # Check 1-letter prefixes
            prefix = first_id[0]
            if prefix in id_prefixes:
                entity_info = id_prefixes[prefix]

        if not entity_info:
            typer.echo(f"Error: Unknown ID prefix in '{first_id}'", err=True)
            raise typer.Exit(1)

        class_name, entity_name = entity_info

        # Import the appropriate entity class
        if class_name == "Works":
            from pyalex import Works

            entity_class = Works
        elif class_name == "Authors":
            from pyalex import Authors

            entity_class = Authors
        elif class_name == "Institutions":
            from pyalex import Institutions

            entity_class = Institutions
        elif class_name == "Sources":
            from pyalex import Sources

            entity_class = Sources
        elif class_name == "Funders":
            from pyalex import Funders

            entity_class = Funders
        elif class_name == "Publishers":
            from pyalex import Publishers

            entity_class = Publishers
        elif class_name == "Topics":
            from pyalex import Topics

            entity_class = Topics
        elif class_name == "Domains":
            from pyalex import Domains

            entity_class = Domains
        elif class_name == "Subfields":
            from pyalex import Subfields

            entity_class = Subfields
        elif class_name == "Fields":
            from pyalex import Fields

            entity_class = Fields
        elif class_name == "Keywords":
            from pyalex import Keywords

            entity_class = Keywords

        if not entity_class:
            typer.echo(
                f"Error: Could not determine entity type for '{first_id}'", err=True
            )
            raise typer.Exit(1)

        # Retrieve entities using async requests only
        import asyncio

        results = asyncio.run(
            _async_retrieve_entities(entity_class, cleaned_ids, class_name)
        )

        # Output results
        _output_results(results, json_path)

    except (CLIError, DataError, ValidationError) as e:
        _handle_cli_exception(e)
        raise typer.Exit(1) from e
    except Exception as e:
        _handle_cli_exception(e)
        raise typer.Exit(1) from e


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
