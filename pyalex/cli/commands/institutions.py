"""
Institutions command for PyAlex CLI.
"""

from typing import Optional

import typer
from typing_extensions import Annotated

from pyalex import Institutions

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


def create_institutions_command(app):
    """Create and register the institutions command."""
    
    @app.command()
    def institutions(
        search: Annotated[Optional[str], typer.Option(
            "--search", "-s",
            help="Search term for institutions"
        )] = None,
        country_code: Annotated[Optional[str], typer.Option(
            "--country",
            help="Filter by country code (e.g. US, UK, CA)"
        )] = None,
        works_count: Annotated[Optional[str], typer.Option(
            "--works-count",
            help="Filter by works count. Use single value (e.g., '1000') or "
                 "range (e.g., '100:5000', ':1000', '500:')"
        )] = None,
        institution_type: Annotated[Optional[str], typer.Option(
            "--type",
            help="Filter by institution type (e.g., 'education', 'healthcare', "
                 "'company', 'archive', 'nonprofit', 'government', 'facility', 'other')"
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
        cited_by_count: Annotated[Optional[str], typer.Option(
            "--cited-by-count",
            help="Filter by total citation count. Use single value (e.g., '1000') or "
                 "range (e.g., '500:5000', ':1000', '1000:')"
        )] = None,
        group_by: Annotated[Optional[str], typer.Option(
            "--group-by",
            help="Group results by field (e.g. 'country_code', 'continent', 'type', "
                 "'cited_by_count', 'works_count')"
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
                 "'display_name:asc')"
        )] = None,
        sample: Annotated[Optional[int], typer.Option(
            "--sample",
            help="Get random sample of results (max 10,000). Use with --seed for "
                 "reproducible results"
        )] = None,
        seed: Annotated[Optional[int], typer.Option(
            "--seed",
            help="Seed for random sampling (used with --sample)"
        )] = 0,
        select: Annotated[Optional[str], typer.Option(
            "--select",
            help="Select specific fields to return (comma-separated). "
                 "Example: 'id,display_name,country_code'. "
                 "If not specified, returns all fields."
        )] = None,
    ):
        """
        Search and retrieve institutions from OpenAlex.
        
        Examples:
          pyalex institutions --search "Harvard"
          pyalex institutions --country US --all
          pyalex institutions --works-count "1000:10000" --limit 50
          pyalex institutions --type education --h-index "50:" --json results.json
          pyalex institutions --country US --two-year-mean-citedness "2.0:" \\
                       --sort-by "works_count:desc"
          pyalex institutions --cited-by-count "10000:" --limit 25
          pyalex institutions --group-by "country_code"
          pyalex institutions --sample 25 --seed 202
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
            
            # Search institutions
            query = Institutions()
            
            if search:
                query = query.search(search)
                
            if country_code:
                query = query.filter(country_code=country_code)
                
            if works_count:
                parsed_works_count = parse_range_filter(works_count)
                query = apply_range_filter(query, 'works_count', parsed_works_count)
                
            if institution_type:
                query = query.filter(type=institution_type)
                
            if h_index:
                parsed_h_index = parse_range_filter(h_index)
                query = apply_range_filter(query, "summary_stats.h_index", parsed_h_index)
                
            if i10_index:
                parsed_i10_index = parse_range_filter(i10_index)
                query = apply_range_filter(query, "summary_stats.i10_index", parsed_i10_index)
                
            if two_year_mean_citedness:
                parsed_citedness = parse_range_filter(two_year_mean_citedness)
                query = apply_range_filter(query, "summary_stats.2yr_mean_citedness", parsed_citedness)
                
            if cited_by_count:
                parsed_cited_by_count = parse_range_filter(cited_by_count)
                query = apply_range_filter(query, 'cited_by_count', parsed_cited_by_count)
            
            # Apply common options (sort, sample, select)
            query = _validate_and_apply_common_options(
                query, all_results, limit, sample, seed, sort_by, select
            )
            
            # Handle group_by parameter
            if group_by:
                query = query.group_by(group_by)
                _print_debug_url(query)
                
                if _dry_run_mode:
                    _print_dry_run_query("Institutions group-by query", url=query.url)
                    return
                
                # For group-by operations, only page 1 is supported (max 200 results)
                results = query.get(per_page=200)
                _print_debug_results(results)
                
                # Output grouped results
                _output_grouped_results(results, json_path)
                return
            
            _print_debug_url(query)
            
            if _dry_run_mode:
                _print_dry_run_query("Institutions query", url=query.url)
                return
            
            if all_results:
                # Get all results using pagination with progress bar
                results = _paginate_with_progress(query, "institutions")
            elif limit is not None:
                # Use smart execution (async or sync based on conditions)
                results = _execute_query_smart(
                    query, all_results=False, limit=limit
                )
            else:
                results = query.get()  # Default first page
            _print_debug_results(results)
            _output_results(results, effective_json_path)
                
        except Exception as e:
            _handle_cli_exception(e)
