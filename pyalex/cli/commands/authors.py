"""
Authors command for PyAlex CLI.
"""

from typing import Annotated

import typer

from pyalex import Authors

from ..batch import add_id_list_option_to_command
from ..command_patterns import execute_standard_query
from ..command_patterns import handle_large_id_list_if_needed
from ..command_patterns import validate_json_output_options
from ..command_patterns import validate_pagination_options
from ..utils import _handle_cli_exception
from ..utils import _output_grouped_results
from ..utils import _output_results
from ..utils import _validate_and_apply_common_options
from ..utils import apply_range_filter
from ..utils import parse_range_filter


def create_authors_command(app):
    """Create and register the authors command."""

    @app.command()
    def authors(
        search: Annotated[
            str | None, typer.Option("--search", "-s", help="Search term for authors")
        ] = None,
        institution_ids: Annotated[
            str | None,
            typer.Option(
                "--institution-ids",
                help="Filter by institution OpenAlex ID(s). Use comma-separated values for "
                "OR logic (e.g., --institution-ids 'I123,I456,I789')",
            ),
        ] = None,
        orcid: Annotated[
            str | None,
            typer.Option(
                "--orcid", help="Filter by ORCID (e.g., '0000-0002-3748-6564')"
            ),
        ] = None,
        works_count: Annotated[
            str | None,
            typer.Option(
                "--works-count",
                help="Filter by works count. Use single value (e.g., '100') or "
                "range (e.g., '50:500', ':200', '100:')",
            ),
        ] = None,
        cited_by_count: Annotated[
            str | None,
            typer.Option(
                "--cited-by-count",
                help="Filter by total citation count. Use single value (e.g., '1000') or "
                "range (e.g., '500:5000', ':1000', '1000:')",
            ),
        ] = None,
        last_known_institution_country: Annotated[
            str | None,
            typer.Option(
                "--last-known-institution-country",
                help="Filter by country code of last known institution (e.g. US, UK, CA)",
            ),
        ] = None,
        h_index: Annotated[
            str | None,
            typer.Option(
                "--h-index",
                help="Filter by h-index from summary stats. Use single value (e.g., '50') "
                "or range (e.g., '10:100', ':50', '25:')",
            ),
        ] = None,
        i10_index: Annotated[
            str | None,
            typer.Option(
                "--i10-index",
                help="Filter by i10-index from summary stats. Use single value "
                "(e.g., '100') or range (e.g., '50:500', ':200', '100:')",
            ),
        ] = None,
        two_year_mean_citedness: Annotated[
            str | None,
            typer.Option(
                "--two-year-mean-citedness",
                help="Filter by 2-year mean citedness from summary stats. Use single value "
                "(e.g., '2.5') or range (e.g., '1.0:5.0', ':3.0', '2.0:')",
            ),
        ] = None,
        group_by: Annotated[
            str | None,
            typer.Option(
                "--group-by",
                help="Group results by field (e.g. 'cited_by_count', 'has_orcid', "
                "'works_count')",
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
        sort_by: Annotated[
            str | None,
            typer.Option(
                "--sort-by",
                help="Sort results by field (e.g. 'cited_by_count:desc', 'works_count', "
                "'display_name:asc'). Multiple sorts: 'works_count:desc,"
                "cited_by_count:desc'",
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
                "Example: 'id,display_name,orcid'. "
                "If not specified, returns all fields.",
            ),
        ] = None,
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
            # Validate options
            validate_pagination_options(all_results, limit)
            effective_json_path = validate_json_output_options(json_flag, json_path)

            # Build query
            query = Authors()

            if search:
                query = query.search(search)
            if institution_ids:
                # Use the generalized helper for ID list handling
                query = add_id_list_option_to_command(
                    query, institution_ids, "authors_institution", Authors
                )
            if orcid:
                query = query.filter(orcid=orcid)

            if works_count:
                parsed_works_count = parse_range_filter(works_count)
                query = apply_range_filter(query, "works_count", parsed_works_count)

            if cited_by_count:
                parsed_cited_by_count = parse_range_filter(cited_by_count)
                query = apply_range_filter(
                    query, "cited_by_count", parsed_cited_by_count
                )

            if last_known_institution_country:
                field_name = "last_known_institution.country_code"
                query = query.filter(**{field_name: last_known_institution_country})

            if h_index:
                parsed_h_index = parse_range_filter(h_index)
                query = apply_range_filter(
                    query, "summary_stats.h_index", parsed_h_index
                )

            if i10_index:
                parsed_i10_index = parse_range_filter(i10_index)
                query = apply_range_filter(
                    query, "summary_stats.i10_index", parsed_i10_index
                )

            if two_year_mean_citedness:
                parsed_citedness = parse_range_filter(two_year_mean_citedness)
                query = apply_range_filter(
                    query, "summary_stats.2yr_mean_citedness", parsed_citedness
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
                query, Authors, all_results, limit, effective_json_path, group_by
            )
            if results is not None:
                return  # Large ID list was handled, we're done

            # Execute normal query
            results = execute_standard_query(
                query, "authors", all_results, limit, group_by
            )

            # Handle output based on query type
            if group_by:
                # Grouped results - use specialized output function
                _output_grouped_results(results, effective_json_path)
                return

            # Handle None results
            if results is None:
                typer.echo("No results returned from API", err=True)
                return

            _output_results(results, effective_json_path)

        except Exception as e:
            _handle_cli_exception(e)
