"""
Authorsfrom ..utils import (
    _validate_and_apply_common_options, _print_debug_url, _print_debug_results,
    _print_dry_run_query, _output_results, _output_grouped_results,
    _handle_cli_exception, _dry_run_mode, parse_range_filter, apply_range_filter,
    _paginate_with_progress, _execute_query_smart
)and for PyAlex CLI.
"""

from typing import Optional

import typer
from typing_extensions import Annotated

from pyalex import Authors

from ..batch import _handle_large_id_list
from ..batch import add_id_list_option_to_command
from ..utils import _debug_mode
from ..utils import _dry_run_mode
from ..utils import _execute_query_smart
from ..utils import _handle_cli_exception
from ..utils import _output_grouped_results
from ..utils import _output_results
from ..utils import _paginate_with_progress
from ..utils import _print_debug_results
from ..utils import _print_debug_url
from ..utils import _print_dry_run_query
from ..utils import _validate_and_apply_common_options
from ..utils import apply_range_filter
from ..utils import parse_range_filter


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
        orcid: Annotated[Optional[str], typer.Option(
            "--orcid",
            help="Filter by ORCID (e.g., '0000-0002-3748-6564')"
        )] = None,
        works_count: Annotated[Optional[str], typer.Option(
            "--works-count",
            help="Filter by works count. Use single value (e.g., '100') or "
                 "range (e.g., '50:500', ':200', '100:')"
        )] = None,
        cited_by_count: Annotated[Optional[str], typer.Option(
            "--cited-by-count",
            help="Filter by total citation count. Use single value (e.g., '1000') or "
                 "range (e.g., '500:5000', ':1000', '1000:')"
        )] = None,
        last_known_institution_country: Annotated[Optional[str], typer.Option(
            "--last-known-institution-country",
            help="Filter by country code of last known institution (e.g. US, UK, CA)"
        )] = None,
        h_index: Annotated[Optional[str], typer.Option(
            "--h-index",
            help="Filter by h-index from summary stats. Use single value (e.g., '50') "
                 "or range (e.g., '10:100', ':50', '25:')"
        )] = None,
        i10_index: Annotated[Optional[str], typer.Option(
            "--i10-index", 
            help="Filter by i10-index from summary stats. Use single value "
                 "(e.g., '100') or range (e.g., '50:500', ':200', '100:')"
        )] = None,
        two_year_mean_citedness: Annotated[Optional[str], typer.Option(
            "--two-year-mean-citedness",
            help="Filter by 2-year mean citedness from summary stats. Use single value "
                 "(e.g., '2.5') or range (e.g., '1.0:5.0', ':3.0', '2.0:')"
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
        json_flag: Annotated[bool, typer.Option(
            "--json",
            help="Output JSON to stdout"
        )] = False,
        json_path: Annotated[Optional[str], typer.Option(
            "--json-file",
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
          pyalex authors --works-count "100:" --cited-by-count "1000:" --limit 50
          pyalex authors --last-known-institution-country US --h-index "25:" \\
                         --json results.json
          pyalex authors --i10-index "50:" --two-year-mean-citedness "2.0:" \\
                         --sort-by "cited_by_count:desc"
          pyalex authors --group-by "has_orcid"
          pyalex authors --sample 25 --seed 456
          pyalex authors --orcid "0000-0002-3748-6564"
        """
        try:
            # Check for mutually exclusive options
            if all_results and limit is not None:
                typer.echo("Error: --all and --limit are mutually exclusive", err=True)
                raise typer.Exit(1)
            
            # Handle JSON output options
            effective_json_path = None
            if json_flag and json_path:
                typer.echo("Error: --json and --json-file are mutually exclusive", err=True)
                raise typer.Exit(1)
            elif json_flag:
                effective_json_path = "-"  # Use "-" to indicate stdout
            elif json_path:
                effective_json_path = json_path
            
            # Search authors
            query = Authors()
            
            if search:
                query = query.search(search)
            if institution_ids:
                # Use the generalized helper for ID list handling
                query = add_id_list_option_to_command(
                    query, institution_ids, 'authors_institution', Authors
                )
            if orcid:
                query = query.filter(orcid=orcid)
            
            if works_count:
                parsed_works_count = parse_range_filter(works_count)
                query = apply_range_filter(query, 'works_count', parsed_works_count)
                
            if cited_by_count:
                parsed_cited_by_count = parse_range_filter(cited_by_count)
                query = apply_range_filter(query, 'cited_by_count', parsed_cited_by_count)
                
            if last_known_institution_country:
                field_name = "last_known_institution.country_code"
                query = query.filter(**{field_name: last_known_institution_country})
                
            if h_index:
                parsed_h_index = parse_range_filter(h_index)
                query = apply_range_filter(query, "summary_stats.h_index", parsed_h_index)
                
            if i10_index:
                parsed_i10_index = parse_range_filter(i10_index)
                query = apply_range_filter(query, "summary_stats.i10_index", parsed_i10_index)
                
            if two_year_mean_citedness:
                parsed_citedness = parse_range_filter(two_year_mean_citedness)
                query = apply_range_filter(query, "summary_stats.2yr_mean_citedness", parsed_citedness)
            
            # Apply common options (sort, sample, select)
            query = _validate_and_apply_common_options(
                query, all_results, limit, sample, seed, sort_by, select
            )

            # Handle group_by parameter
            if group_by:
                query = query.group_by(group_by)
                _print_debug_url(query)
                
                # For group-by operations, only page 1 is supported (max 200 results)
                results = query.get(per_page=200)
                _print_debug_results(results)
                
                # Output grouped results
                _output_grouped_results(results, json_path)
                return
            
            _print_debug_url(query)
            
            try:
                # Check if we need to handle any large ID lists
                large_id_attrs = [
                    attr for attr in dir(query) if attr.startswith('_large_')
                ]
                
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
                        # Get all results using pagination with progress bar
                        results = _paginate_with_progress(query, "authors")
                    elif limit is not None:
                        # Use smart execution (async or sync based on conditions)
                        results = _execute_query_smart(
                            query, all_results=False, limit=limit
                        )
                    else:
                        results = query.get()  # Default first page
                
                _print_debug_results(results)
                _output_results(results, effective_json_path)
                    
            except Exception as api_error:
                if _debug_mode:
                    from pyalex.logger import get_logger
                    logger = get_logger()
                    logger.debug(f"API call failed: {api_error}")
                raise
                
        except Exception as e:
            _handle_cli_exception(e)
