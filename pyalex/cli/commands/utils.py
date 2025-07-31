"""
Utility commands for PyAlex CLI.
"""

import json
import sys
from typing import Optional

import typer
from typing_extensions import Annotated

from ..utils import (
    _clean_ids, _async_retrieve_entities, _sync_retrieve_entities,
    _output_results, _handle_cli_exception, _debug_mode
)


def from_ids(
    json_path: Annotated[Optional[str], typer.Option(
        "--json",
        help="Save results to JSON file at specified path"
    )] = None,
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
            raise typer.Exit(1)
        
        # Extract IDs from input
        ids = []
        entity_class = None
        
        if isinstance(data, dict):
            # Single entity object
            if 'id' in data:
                ids = [data['id']]
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
                    if 'id' in item:
                        ids.append(item['id'])
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
            'W': ('Works', 'works'),
            'A': ('Authors', 'authors'),
            'I': ('Institutions', 'institutions'),
            'S': ('Sources', 'sources'),
            'F': ('Funders', 'funders'),
            'P': ('Publishers', 'publishers'),
            'T': ('Topics', 'topics'),
            'D': ('Domains', 'domains'),
            'SF': ('Subfields', 'subfields'),
            'FI': ('Fields', 'fields'),
            'K': ('Keywords', 'keywords'),
        }
        
        # Check for 2-letter prefixes first, then 1-letter
        entity_info = None
        for prefix in ['SF', 'FI']:  # Check 2-letter prefixes first
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
        if class_name == 'Works':
            from pyalex import Works
            entity_class = Works
        elif class_name == 'Authors':
            from pyalex import Authors
            entity_class = Authors
        elif class_name == 'Institutions':
            from pyalex import Institutions
            entity_class = Institutions
        elif class_name == 'Sources':
            from pyalex import Sources
            entity_class = Sources
        elif class_name == 'Funders':
            from pyalex import Funders
            entity_class = Funders
        elif class_name == 'Publishers':
            from pyalex import Publishers
            entity_class = Publishers
        elif class_name == 'Topics':
            from pyalex import Topics
            entity_class = Topics
        elif class_name == 'Domains':
            from pyalex import Domains
            entity_class = Domains
        elif class_name == 'Subfields':
            from pyalex import Subfields
            entity_class = Subfields
        elif class_name == 'Fields':
            from pyalex import Fields
            entity_class = Fields
        elif class_name == 'Keywords':
            from pyalex import Keywords
            entity_class = Keywords
        
        if not entity_class:
            typer.echo(f"Error: Could not determine entity type for '{first_id}'", err=True)
            raise typer.Exit(1)
        
        # Retrieve entities
        try:
            # Try async first for better performance
            import asyncio
            try:
                results = asyncio.run(
                    _async_retrieve_entities(entity_class, cleaned_ids, class_name)
                )
            except ImportError:
                # Fall back to sync if aiohttp not available
                results = _sync_retrieve_entities(entity_class, cleaned_ids, class_name)
        except Exception:
            # Fall back to sync on any async error
            results = _sync_retrieve_entities(entity_class, cleaned_ids, class_name)
        
        # Output results
        _output_results(results, json_path)
        
    except Exception as e:
        _handle_cli_exception(e)


def show(
    file_path: Annotated[Optional[str], typer.Argument(
        help="Path to the JSON file to display (if not provided, reads from stdin)"
    )] = None,
    json_path: Annotated[Optional[str], typer.Option(
        "--json",
        help="Save results to JSON file at specified path"
    )] = None,
):
    """
    Display a JSON file containing OpenAlex data in table format.
    
    Takes a JSON file as input and displays it in a formatted table.
    Can read from a file or from stdin if no file is provided.
    
    Examples:
      pyalex show results.json
      cat results.json | pyalex show
      pyalex show data.json --json reformatted.json
    """
    try:
        # Read JSON data
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
            except FileNotFoundError:
                typer.echo(f"Error: File '{file_path}' not found", err=True)
                raise typer.Exit(1)
            except json.JSONDecodeError as e:
                typer.echo(f"Error: Invalid JSON in file '{file_path}': {e}", err=True)
                raise typer.Exit(1)
        else:
            # Read from stdin
            input_data = sys.stdin.read().strip()
            if not input_data:
                typer.echo("Error: No input provided", err=True)
                raise typer.Exit(1)
            
            try:
                data = json.loads(input_data)
            except json.JSONDecodeError as e:
                typer.echo(f"Error: Invalid JSON input: {e}", err=True)
                raise typer.Exit(1)
        
        # Display the data
        if isinstance(data, dict):
            # Check if this is a grouped result (contains group_by field)
            if 'group_by' in data and isinstance(data['group_by'], list):
                # This is grouped data from --group-by option
                _output_results(data['group_by'], json_path, grouped=True)
            else:
                # Single entity
                _output_results(data, json_path, single=True)
        elif isinstance(data, list):
            # Check if this is a list of grouped items (key, key_display_name, count)
            if (data and len(data) > 0 and isinstance(data[0], dict) and 
                all(key in data[0] for key in ['key', 'key_display_name', 'count']) and
                len(data[0]) == 3):
                # This is grouped data
                _output_results(data, json_path, grouped=True)
            else:
                # List of entities
                _output_results(data, json_path)
        else:
            typer.echo("Error: Input must be a JSON object or array", err=True)
            raise typer.Exit(1)
            
    except Exception as e:
        _handle_cli_exception(e)


def create_utils_commands(app):
    """Register utility commands with the app."""
    app.command()(from_ids)
    app.command()(show)
