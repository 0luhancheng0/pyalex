"""
Simple entity commands template for PyAlex CLI.

This module contains basic implementations for entity commands that follow a common pattern.
"""

from typing import Optional

import typer
from typing_extensions import Annotated

from pyalex import Topics, Sources, Institutions, Publishers, Funders, Domains, Fields, Subfields, Keywords
from ..utils import (
    _validate_and_apply_common_options, _print_debug_url, _print_debug_results,
    _print_dry_run_query, _output_results, _output_grouped_results,
    _handle_cli_exception, _dry_run_mode
)


def create_simple_entity_command(app, entity_class, entity_name, entity_name_lower):
    """Create a simple entity command with standard options."""
    
    def command_func(
        search: Annotated[Optional[str], typer.Option(
            "--search", "-s",
            help=f"Search term for {entity_name_lower}"
        )] = None,
        group_by: Annotated[Optional[str], typer.Option(
            "--group-by",
            help="Group results by field"
        )] = None,
        all_results: Annotated[bool, typer.Option(
            "--all",
            help="Retrieve all results (default: first page only)"
        )] = False,
        limit: Annotated[Optional[int], typer.Option(
            "--limit", "-l",
            help="Maximum number of results to return (mutually exclusive with --all)"
        )] = None,
        json_path: Annotated[Optional[str], typer.Option(
            "--json",
            help="Save results to JSON file at specified path"
        )] = None,
        sort_by: Annotated[Optional[str], typer.Option(
            "--sort-by",
            help="Sort results by field"
        )] = None,
        sample: Annotated[Optional[int], typer.Option(
            "--sample",
            help="Get random sample of results (max 10,000)"
        )] = None,
        seed: Annotated[Optional[int], typer.Option(
            "--seed",
            help="Seed for random sampling (used with --sample)"
        )] = 0,
        select: Annotated[Optional[str], typer.Option(
            "--select",
            help="Select specific fields to return (comma-separated)"
        )] = None,
    ):
        f"""
        Search and retrieve {entity_name_lower} from OpenAlex.
        
        Examples:
          pyalex {entity_name_lower} --search "example"
          pyalex {entity_name_lower} --all
          pyalex {entity_name_lower} --limit 50 --json results.json
        """
        try:
            # Check for mutually exclusive options
            if all_results and limit is not None:
                typer.echo("Error: --all and --limit are mutually exclusive", err=True)
                raise typer.Exit(1)
            
            # Create query
            query = entity_class()
            
            if search:
                query = query.search(search)
            
            # Apply common options
            query = _validate_and_apply_common_options(
                query, all_results, limit, sample, seed, sort_by, select
            )

            # Handle group_by parameter
            if group_by:
                query = query.group_by(group_by)
                _print_debug_url(query)
                
                results = query.get(limit=100000)
                _print_debug_results(results)
                _output_grouped_results(results, json_path)
                return
            
            _print_debug_url(query)
            
            if _dry_run_mode:
                _print_dry_run_query(
                    f"{entity_name} query",
                    url=query.url
                )
                return
            
            if all_results:
                limit_to_use = None
            elif limit is not None:
                limit_to_use = limit
            else:
                limit_to_use = 25
            
            results = query.get(limit=limit_to_use)
            _print_debug_results(results)
            _output_results(results, json_path)
                
        except Exception as e:
            _handle_cli_exception(e)
    
    # Set proper function name and docstring
    command_func.__name__ = entity_name_lower
    return command_func


def create_entity_commands(app):
    """Create and register all simple entity commands."""
    
    # Topics
    topics_func = create_simple_entity_command(app, Topics, "Topics", "topics")
    app.command()(topics_func)
    
    # Sources
    sources_func = create_simple_entity_command(app, Sources, "Sources", "sources")
    app.command()(sources_func)
    
    # Institutions
    institutions_func = create_simple_entity_command(app, Institutions, "Institutions", "institutions")
    app.command()(institutions_func)
    
    # Publishers
    publishers_func = create_simple_entity_command(app, Publishers, "Publishers", "publishers")
    app.command()(publishers_func)
    
    # Funders
    funders_func = create_simple_entity_command(app, Funders, "Funders", "funders")
    app.command()(funders_func)
    
    # Domains
    domains_func = create_simple_entity_command(app, Domains, "Domains", "domains")
    app.command()(domains_func)
    
    # Fields
    fields_func = create_simple_entity_command(app, Fields, "Fields", "fields")
    app.command()(fields_func)
    
    # Subfields
    subfields_func = create_simple_entity_command(app, Subfields, "Subfields", "subfields")
    app.command()(subfields_func)
    
    # Keywords
    keywords_func = create_simple_entity_command(app, Keywords, "Keywords", "keywords")
    app.command()(keywords_func)
