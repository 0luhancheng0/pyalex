"""
Works command for PyAlex CLI.
"""

import datetime
from typing import Annotated

import typer

from pyalex import Works

from ..batch import add_id_list_option_to_command
from ..command_patterns import execute_standard_query
from ..command_patterns import handle_large_id_list_if_needed
from ..command_patterns import validate_output_format_options
from ..command_patterns import validate_pagination_options
from ..utils import _add_abstract_to_work
from ..utils import _handle_cli_exception
from ..utils import _output_grouped_results
from ..utils import _output_results
from ..utils import _validate_and_apply_common_options


def create_works_command(app):
    """Create and register the works command."""

    @app.command()
    def works(
        search: Annotated[
            str | None, typer.Option("--search", "-s", help="Search term for works")
        ] = None,
        author_ids: Annotated[
            str | None,
            typer.Option(
                "--author-ids",
                help="Filter by author OpenAlex ID(s). Use comma-separated values for "
                "OR logic (e.g., --author-ids 'A123,A456,A789')",
            ),
        ] = None,
        institution_ids: Annotated[
            str | None,
            typer.Option(
                "--institution-ids",
                help="Filter by institution OpenAlex ID(s). Use comma-separated values for "
                "OR logic (e.g., --institution-ids 'I123,I456,I789')",
            ),
        ] = None,
        publication_year: Annotated[
            str | None,
            typer.Option(
                "--year",
                help="Filter by publication year (e.g. '2020' or range '2019:2021')",
            ),
        ] = None,
        publication_date: Annotated[
            str | None,
            typer.Option(
                "--date",
                help="Filter by publication date (e.g. '2020-01-01' or "
                "range '2019-01-01:2020-12-31')",
            ),
        ] = None,
        work_type: Annotated[
            str | None,
            typer.Option(
                "--type", help="Filter by work type (e.g. 'article', 'book', 'dataset')"
            ),
        ] = None,
        topic_ids: Annotated[
            str | None,
            typer.Option(
                "--topic-ids",
                help="Filter by primary topic OpenAlex ID(s). Use comma-separated values for "
                "OR logic (e.g., --topic-ids 'T123,T456,T789')",
            ),
        ] = None,
        subfield_ids: Annotated[
            str | None,
            typer.Option(
                "--subfield-ids",
                help="Filter by primary topic subfield OpenAlex ID(s). Use comma-separated values for "
                "OR logic (e.g., --subfield-ids 'SF123,SF456,SF789')",
            ),
        ] = None,
        funder_ids: Annotated[
            str | None,
            typer.Option(
                "--funder-ids",
                help="Filter by funder OpenAlex ID(s). Use comma-separated values for "
                "OR logic (e.g., --funder-ids 'F123,F456,F789')",
            ),
        ] = None,
        award_ids: Annotated[
            str | None,
            typer.Option(
                "--award-ids",
                help="Filter by grant award ID(s). Use comma-separated values for "
                "OR logic (e.g., --award-ids 'AWARD123,AWARD456')",
            ),
        ] = None,
        group_by: Annotated[
            str | None,
            typer.Option(
                "--group-by",
                help="Group results by field (e.g. 'oa_status', 'publication_year', "
                "'type', 'is_retracted', 'cited_by_count')",
            ),
        ] = None,
        all_results: Annotated[
            bool,
            typer.Option(
                "--all", help="Retrieve all results (default: first page only)"
            ),
        ] = False,
        limit: Annotated[
            int | None,
            typer.Option(
                "--limit",
                "-l",
                help="Maximum number of results to return (mutually exclusive with --all)",
            ),
        ] = None,
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
        sort_by: Annotated[
            str | None,
            typer.Option(
                "--sort-by",
                help="Sort results by field (e.g. 'cited_by_count:desc', 'publication_year', "
                "'display_name:asc'). Multiple sorts: 'year:desc,cited_by_count:desc'",
            ),
        ] = None,
        sample: Annotated[
            int | None,
            typer.Option(
                "--sample",
                help="Get random sample of results (max 10,000). "
                "Use with --seed for reproducible results",
            ),
        ] = None,
        seed: Annotated[
            int | None,
            typer.Option(
                "--seed", help="Seed for random sampling (used with --sample)"
            ),
        ] = 0,
        select: Annotated[
            str | None,
            typer.Option(
                "--select",
                help="Select specific fields to return (comma-separated). "
                "Example: 'id,doi,title,display_name'. "
                "If not specified, returns all fields.",
            ),
        ] = None,
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
            # Validate options
            validate_pagination_options(all_results, limit)
            effective_json_path, effective_parquet_path = (
                validate_output_format_options(json_flag, json_path, parquet_path)
            )

            # Build query
            query = Works()

            if search:
                query = query.search(search)

            if author_ids:
                # Use the generalized helper for ID list handling
                query = add_id_list_option_to_command(
                    query, author_ids, "works_author", Works
                )

            if institution_ids:
                # Use the generalized helper for ID list handling
                query = add_id_list_option_to_command(
                    query, institution_ids, "works_institution", Works
                )

            if publication_year:
                # Handle publication year ranges (e.g., "2019:2020") or single years
                if ":" in publication_year:
                    try:
                        start_year, end_year = publication_year.split(":")
                        start_year = int(start_year.strip())
                        end_year = int(end_year.strip())
                        query = query.filter_by_publication_year(
                            start_year=start_year, end_year=end_year
                        )
                    except ValueError:
                        typer.echo(
                            "Error: Invalid year range format. Use 'start:end' "
                            "(e.g., '2019:2020')",
                            err=True,
                        )
                        raise typer.Exit(1) from None
                else:
                    try:
                        year = int(publication_year.strip())
                        query = query.filter_by_publication_year(year=year)
                    except ValueError:
                        typer.echo(
                            "Error: Invalid year format. Use a single year or range "
                            "(e.g., '2020' or '2019:2020')",
                            err=True,
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

                        query = query.filter_by_publication_date(
                            start_date=start_date, end_date=end_date
                        )
                    except ValueError as ve:
                        typer.echo(
                            "Error: Invalid date range format. Use "
                            "'YYYY-MM-DD:YYYY-MM-DD' (e.g., '2019-01-01:2020-12-31')",
                            err=True,
                        )
                        raise typer.Exit(1) from ve
                else:
                    try:
                        # Validate single date format
                        datetime.datetime.strptime(publication_date.strip(), "%Y-%m-%d")
                        query = query.filter_by_publication_date(
                            date=publication_date.strip()
                        )
                    except ValueError:
                        typer.echo(
                            "Error: Invalid date format. Use YYYY-MM-DD format "
                            "(e.g., '2020-01-01') or range '2019-01-01:2020-12-31'",
                            err=True,
                        )
                        raise typer.Exit(1) from None

            if work_type:
                query = query.filter_by_type(work_type)

            if topic_ids:
                # Use the generalized helper for ID list handling
                query = add_id_list_option_to_command(
                    query, topic_ids, "works_topic", Works
                )

            if subfield_ids:
                # Use the generalized helper for ID list handling
                query = add_id_list_option_to_command(
                    query, subfield_ids, "works_subfield", Works
                )

            if funder_ids:
                # Use the generalized helper for ID list handling
                query = add_id_list_option_to_command(
                    query, funder_ids, "works_funder", Works
                )

            if award_ids:
                # Use the generalized helper for ID list handling
                query = add_id_list_option_to_command(
                    query, award_ids, "works_award", Works
                )

            # Apply common options (sort, sample, select)
            query = _validate_and_apply_common_options(
                query, all_results, limit, sample, seed, sort_by, select
            )

            # Apply group_by parameter
            if group_by:
                query = query.group_by(group_by)

            # Check for and handle large ID lists (batch processing)
            results = handle_large_id_list_if_needed(
                query, Works, all_results, limit, effective_json_path, group_by
            )
            if results is not None:
                return  # Large ID list was handled, we're done

            # Execute normal query
            results = execute_standard_query(
                query, "works", all_results, limit, group_by
            )

            # Handle output based on query type
            if group_by:
                # Grouped results - use specialized output function
                _output_grouped_results(
                    results, effective_json_path, effective_parquet_path
                )
                return

            # Handle None or empty results
            if results is None:
                typer.echo("No results returned from API", err=True)
                return

            # Convert results to list format for normal (non-grouped) queries
            import pandas as pd

            if isinstance(results, pd.DataFrame):
                results_list = results.to_dict("records")
            elif hasattr(results, "to_dict") and callable(results.to_dict):
                results_list = results.to_dict("records")
            elif isinstance(results, list):
                results_list = results
            else:
                results_list = list(results) if results is not None else []

            # Add abstracts to works
            if len(results_list) > 0:
                results_list = [_add_abstract_to_work(work) for work in results_list]

            _output_results(
                results_list, effective_json_path, effective_parquet_path
            )

        except Exception as e:
            _handle_cli_exception(e)
