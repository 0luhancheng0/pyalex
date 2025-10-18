"""
Works command for PyAlex CLI.
"""

import datetime
from typing import Optional

import typer
from typing_extensions import Annotated

from pyalex import Works

from ..batch import _handle_large_id_list
from ..batch import add_id_list_option_to_command
from ..utils import _add_abstract_to_work
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


def create_works_command(app):
    """Create and register the works command."""
    
    @app.command()
    def works(
        search: Annotated[Optional[str], typer.Option(
            "--search", "-s",
            help="Search term for works"
        )] = None,
        author_ids: Annotated[Optional[str], typer.Option(
            "--author-ids",
            help="Filter by author OpenAlex ID(s). Use comma-separated values for "
                 "OR logic (e.g., --author-ids 'A123,A456,A789')"
        )] = None,
        institution_ids: Annotated[Optional[str], typer.Option(
            "--institution-ids", 
            help="Filter by institution OpenAlex ID(s). Use comma-separated values for "
                 "OR logic (e.g., --institution-ids 'I123,I456,I789')"
        )] = None,
        publication_year: Annotated[Optional[str], typer.Option(
            "--year",
            help="Filter by publication year (e.g. '2020' or range '2019:2021')"
        )] = None,
        publication_date: Annotated[Optional[str], typer.Option(
            "--date",
            help="Filter by publication date (e.g. '2020-01-01' or "
                 "range '2019-01-01:2020-12-31')"
        )] = None,
        work_type: Annotated[Optional[str], typer.Option(
            "--type",
            help="Filter by work type (e.g. 'article', 'book', 'dataset')"
        )] = None,
        topic_ids: Annotated[Optional[str], typer.Option(
            "--topic-ids",
            help="Filter by primary topic OpenAlex ID(s). Use comma-separated values for "
                 "OR logic (e.g., --topic-ids 'T123,T456,T789')"
        )] = None,
        subfield_ids: Annotated[Optional[str], typer.Option(
            "--subfield-ids",
            help="Filter by primary topic subfield OpenAlex ID(s). Use comma-separated values for "
                 "OR logic (e.g., --subfield-ids 'SF123,SF456,SF789')"
        )] = None,
        funder_ids: Annotated[Optional[str], typer.Option(
            "--funder-ids",
            help="Filter by funder OpenAlex ID(s). Use comma-separated values for "
                 "OR logic (e.g., --funder-ids 'F123,F456,F789')"
        )] = None,
        award_ids: Annotated[Optional[str], typer.Option(
            "--award-ids",
            help="Filter by grant award ID(s). Use comma-separated values for "
                 "OR logic (e.g., --award-ids 'AWARD123,AWARD456')"
        )] = None,
        group_by: Annotated[Optional[str], typer.Option(
            "--group-by",
            help="Group results by field (e.g. 'oa_status', 'publication_year', "
                 "'type', 'is_retracted', 'cited_by_count')"
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
            help="Sort results by field (e.g. 'cited_by_count:desc', 'publication_year', "
                 "'display_name:asc'). Multiple sorts: 'year:desc,cited_by_count:desc'"
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
                 "Example: 'id,doi,title,display_name'. "
                 "If not specified, returns all fields."
        )] = None,
    ):
        """
        Search and retrieve works from OpenAlex.
        
        Examples:
          pyalex works --search "machine learning"
          pyalex works --author-ids "A1234567890" --all
          pyalex works --author-ids "A123,A456,A789" --limit 50
          pyalex works --year "2019:2020" --json results.json
          pyalex works --date "2020-01-01:2020-12-31" --all
          pyalex works --date "2020-06-15"
          pyalex works --type "article" --search "COVID-19"
          pyalex works --topic-ids "T10002"
          pyalex works --topic-ids "T123,T456,T789" --all
          pyalex works --subfield-ids "SF12345"
          pyalex works --subfield-ids "SF123,SF456" --all
          pyalex works --institution-ids "I27837315"
          pyalex works --institution-ids "I123,I456,I789" --all
          pyalex works --funder-ids "F4320332161"
          pyalex works --funder-ids "F123,F456,F789" --all
          pyalex works --award-ids "AWARD123,AWARD456"
          pyalex works --search "AI" --json ai_works.json
          pyalex works --group-by "oa_status"
          pyalex works --group-by "publication_year" --search "COVID-19"
          pyalex works --sort-by "cited_by_count:desc" --limit 100
          pyalex works --sample 50 --seed 123
          pyalex works --search "climate change" \\
            --sort-by "publication_year:desc,cited_by_count:desc"
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
            
            # Search works
            query = Works()
            
            if search:
                query = query.search(search)
            if author_ids:
                # Use the generalized helper for ID list handling
                query = add_id_list_option_to_command(
                    query, author_ids, 'works_author', Works
                )
            if institution_ids:
                # Use the generalized helper for ID list handling
                query = add_id_list_option_to_command(
                    query, institution_ids, 'works_institution', Works
                )
            
            if publication_year:
                # Handle publication year ranges (e.g., "2019:2020") or single years
                if ":" in publication_year:
                    try:
                        start_year, end_year = publication_year.split(":")
                        start_year = int(start_year.strip())
                        end_year = int(end_year.strip())
                        
                        # For inclusive range, use >= start_year and <= end_year
                        # Since PyAlex only supports > and <, we'll use 
                        # (start_year - 1) and (end_year + 1)
                        query = query.filter_gt(publication_year=start_year - 1)
                        query = query.filter_lt(publication_year=end_year + 1)
                    except ValueError:
                        typer.echo(
                            "Error: Invalid year range format. Use 'start:end' "
                            "(e.g., '2019:2020')", 
                            err=True
                        )
                        raise typer.Exit(1) from None
                else:
                    try:
                        year = int(publication_year.strip())
                        query = query.filter(publication_year=year)
                    except ValueError:
                        typer.echo(
                            "Error: Invalid year format. Use a single year or range "
                            "(e.g., '2020' or '2019:2020')", 
                            err=True
                        )
                        raise typer.Exit(1) from None
        
            if publication_date:
                # Handle publication date ranges (e.g., "2019-01-01:2020-12-31") 
                # or single dates
                if ":" in publication_date:
                    try:
                        start_date, end_date = publication_date.split(":")
                        start_date = start_date.strip()
                        end_date = end_date.strip()
                        
                        # Validate date format (basic check for YYYY-MM-DD)
                        datetime.datetime.strptime(start_date, "%Y-%m-%d")
                        datetime.datetime.strptime(end_date, "%Y-%m-%d")
                        
                        # For inclusive range, we need >= start_date and <= end_date
                        # We'll use from_publication_date and to_publication_date
                        query = query.filter(from_publication_date=start_date)
                        query = query.filter(to_publication_date=end_date)
                    except ValueError as ve:
                        typer.echo(
                            "Error: Invalid date range format. Use "
                            "'YYYY-MM-DD:YYYY-MM-DD' (e.g., '2019-01-01:2020-12-31')", 
                            err=True
                        )
                        raise typer.Exit(1) from ve
                else:
                    try:
                        # Validate single date format
                        datetime.datetime.strptime(publication_date.strip(), "%Y-%m-%d")
                        query = query.filter(publication_date=publication_date.strip())
                    except ValueError:
                        typer.echo(
                            "Error: Invalid date format. Use YYYY-MM-DD format "
                            "(e.g., '2020-01-01') or range '2019-01-01:2020-12-31'", 
                            err=True
                        )
                        raise typer.Exit(1) from None
            
            if work_type:
                query = query.filter(type=work_type)
            
            if topic_ids:
                # Use the generalized helper for ID list handling
                query = add_id_list_option_to_command(
                    query, topic_ids, 'works_topic', Works
                )
            
            if subfield_ids:
                # Use the generalized helper for ID list handling
                query = add_id_list_option_to_command(
                    query, subfield_ids, 'works_subfield', Works
                )
            
            if funder_ids:
                # Use the generalized helper for ID list handling
                query = add_id_list_option_to_command(
                    query, funder_ids, 'works_funder', Works
                )
            
            if award_ids:
                # Use the generalized helper for ID list handling
                query = add_id_list_option_to_command(
                    query, award_ids, 'works_award', Works
                )

            # Apply common options (sort, sample, select)
            query = _validate_and_apply_common_options(
                query, all_results, limit, sample, seed, sort_by, select
            )

            # Apply group_by parameter BEFORE checking for large ID lists
            # so it gets preserved in batch processing
            if group_by:
                query = query.group_by(group_by)

            # Check if we need to handle any large ID lists AFTER group_by processing
            large_id_attrs = [attr for attr in dir(query) 
                             if attr.startswith('_large_')]
            
            if large_id_attrs:
                # Handle large ID list using the generalized system
                attr_name = large_id_attrs[0]  # Take the first one found
                large_id_list = getattr(query, attr_name)
                delattr(query, attr_name)
                
                # Extract the filter config key from the attribute name
                # e.g., '_large_works_funder_list' -> 'works_funder'
                filter_config_key = (attr_name.replace('_large_', '')
                                   .replace('_list', ''))
                
                results = _handle_large_id_list(
                    query,
                    large_id_list,
                    filter_config_key,
                    Works,
                    filter_config_key.split('_')[1] + " IDs",  # e.g., "funder IDs"
                    all_results,
                    limit,
                    json_path=effective_json_path
                )
                
                # Check if results is None or empty
                if results is None:
                    typer.echo("No results returned from API", err=True)
                    return
                
                # For grouped results, use the appropriate output function
                if group_by:
                    _output_grouped_results(results, effective_json_path)
                else:
                    # Always convert abstracts for all works in results
                    if results:
                        results = [_add_abstract_to_work(work) for work in results]
                    _output_results(results, effective_json_path)
                return

            # Print debug URL before making the request
            _print_debug_url(query)
            
            # Normal single query execution (no large ID lists to handle at this point)
            try:
                if _dry_run_mode:
                    _print_dry_run_query(
                        "Works query",
                        url=query.url
                    )
                    return
                
                # Execute the query based on type
                if group_by:
                    # For group-by operations, only page 1 is supported (max 200 results)
                    results = query.get(per_page=200)
                    _print_debug_results(results)
                    # Output grouped results
                    _output_grouped_results(results, effective_json_path)
                    return
                
                # Normal works query execution
                if all_results:
                    # Get all results using pagination with progress bar
                    results = _paginate_with_progress(query, "works")
                elif limit is not None:
                    # Use smart execution (async or sync based on conditions)
                    results = _execute_query_smart(
                        query, all_results=False, limit=limit
                    )
                else:
                    results = query.get()  # Default first page
                
                _print_debug_results(results)
            except Exception as api_error:
                if _debug_mode:
                    from pyalex.logger import get_logger
                    logger = get_logger()
                    logger.debug(f"API call failed: {api_error}")
                raise
            
            # Check if results is None or empty
            if results is None:
                typer.echo("No results returned from API", err=True)
                return
            
            # Always convert abstracts for all works in results
            if results:
                results = [_add_abstract_to_work(work) for work in results]
            _output_results(results, effective_json_path)
                
        except Exception as e:
            _handle_cli_exception(e)
