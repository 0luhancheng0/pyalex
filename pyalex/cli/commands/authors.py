"""
Authors command for PyAlex CLI.
"""

from typing import Optional

import typer
from typing_extensions import Annotated

from pyalex import Authors
from ..batch import add_id_list_option_to_command, _handle_large_id_list
from ..utils import (
    _validate_and_apply_common_options, _print_debug_url, _print_debug_results,
    _print_dry_run_query, _output_results, _output_grouped_results,
    _handle_cli_exception, _debug_mode, _dry_run_mode
)


def create_authors_command(app):
    """Create and register the authors command."""
    
    @app.command()
    def authors(
        search: Annotated[Optional[str], typer.Option(
            "--search", "-s",
            help="Search term for authors"
        )] = None,
        institution_ids: Annotated[Optional[str], typer.Option(
            "--institution-ids",
            help="Filter by institution OpenAlex ID(s). Use comma-separated values for "
                 "OR logic (e.g., --institution-ids 'I123,I456,I789')"
        )] = None,
        group_by: Annotated[Optional[str], typer.Option(
            "--group-by",
            help="Group results by field (e.g. 'cited_by_count', 'has_orcid', "
                 "'works_count')"
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
            help="Sort results by field (e.g. 'cited_by_count:desc', 'works_count', "
                 "'display_name:asc'). Multiple sorts: 'works_count:desc,"
                 "cited_by_count:desc'"
        )] = None,
        sample: Annotated[Optional[int], typer.Option(
            "--sample",
            help="Get random sample of results (max 10,000). "
                 "Use with --seed for reproducible results"
        )] = None,
        seed: Annotated[Optional[int], typer.Option(
            "--seed",
            help="Seed for random sampling (used with --sample)"
        )] = 0,
        select: Annotated[Optional[str], typer.Option(
            "--select",
            help="Select specific fields to return (comma-separated). "
                 "Example: 'id,display_name,orcid'. "
                 "If not specified, returns all fields."
        )] = None,
    ):
        """
        Search and retrieve authors from OpenAlex.
        
        Examples:
          pyalex authors --search "John Smith"
          pyalex authors --institution-ids "I1234567890" --all
          pyalex authors --institution-ids "I123,I456,I789" --limit 50
          pyalex authors --group-by "cited_by_count" --json results.json
          pyalex authors --group-by "has_orcid"
          pyalex authors --sort-by "cited_by_count:desc" --limit 100
          pyalex authors --sample 25 --seed 456
        """
        try:
            # Check for mutually exclusive options
            if all_results and limit is not None:
                typer.echo("Error: --all and --limit are mutually exclusive", err=True)
                raise typer.Exit(1)
            
            # Search authors
            query = Authors()
            
            if search:
                query = query.search(search)
            if institution_ids:
                # Use the generalized helper for ID list handling
                query = add_id_list_option_to_command(
                    query, institution_ids, 'authors_institution', Authors
                )
            
            # Apply common options (sort, sample, select)
            query = _validate_and_apply_common_options(
                query, all_results, limit, sample, seed, sort_by, select
            )

            # Handle group_by parameter
            if group_by:
                query = query.group_by(group_by)
                _print_debug_url(query)
                
                # For group-by operations, retrieve all groups by default
                results = query.get(limit=100000)  # High limit to get all groups
                _print_debug_results(results)
                
                # Output grouped results
                _output_grouped_results(results, json_path)
                return
            
            _print_debug_url(query)
            
            try:
                # Check if we need to handle any large ID lists
                large_id_attrs = [attr for attr in dir(query) if attr.startswith('_large_')]
                
                if large_id_attrs:
                    # Handle large ID list using the generalized system
                    attr_name = large_id_attrs[0]  # Take the first one found
                    large_id_list = getattr(query, attr_name)
                    delattr(query, attr_name)
                    
                    # Extract the filter config key from the attribute name
                    filter_config_key = (attr_name.replace('_large_', '')
                                       .replace('_list', ''))
                    
                    results = _handle_large_id_list(
                        query,
                        large_id_list,
                        filter_config_key,
                        Authors,
                        filter_config_key.split('_')[1] + " IDs",
                        all_results,
                        limit,
                        json_path
                    )
                else:
                    # Standard single query execution
                    if _dry_run_mode:
                        _print_dry_run_query(
                            "Authors query",
                            url=query.url
                        )
                        return
                    
                    if all_results:
                        limit_to_use = None  # Get all results
                    elif limit is not None:
                        limit_to_use = limit  # Use specified limit
                    else:
                        limit_to_use = 25  # Default first page
                    results = query.get(limit=limit_to_use)
                
                _print_debug_results(results)
                _output_results(results, json_path)
                    
            except Exception as api_error:
                if _debug_mode:
                    from pyalex.logger import get_logger
                    logger = get_logger()
                    logger.debug(f"API call failed: {api_error}")
                raise
                
        except Exception as e:
            _handle_cli_exception(e)
