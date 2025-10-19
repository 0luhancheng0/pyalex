"""
Institutions command for PyAlex CLI.
"""

from typing import Annotated

import typer

from pyalex import Institutions

from ..command_patterns import execute_standard_query
from ..command_patterns import validate_output_format_options
from ..command_patterns import validate_pagination_options
from ..utils import _handle_cli_exception
from ..utils import _output_grouped_results
from ..utils import _output_results
from ..utils import _validate_and_apply_common_options
from ..utils import apply_range_filter
from ..utils import parse_range_filter


def create_institutions_command(app):
    """Create and register the institutions command."""

    @app.command()
    def institutions(
        search: Annotated[
            str | None,
            typer.Option("--search", "-s", help="Search term for institutions"),
        ] = None,
        country_code: Annotated[
            str | None,
            typer.Option("--country", help="Filter by country code (e.g. US, UK, CA)"),
        ] = None,
        works_count: Annotated[
            str | None,
            typer.Option(
                "--works-count",
                help="Filter by works count. Use single value (e.g., '1000') or "
                "range (e.g., '100:5000', ':1000', '500:')",
            ),
        ] = None,
        institution_type: Annotated[
            str | None,
            typer.Option(
                "--type",
                help="Filter by institution type (e.g., 'education', 'healthcare', "
                "'company', 'archive', 'nonprofit', 'government', 'facility', 'other')",
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
        cited_by_count: Annotated[
            str | None,
            typer.Option(
                "--cited-by-count",
                help="Filter by total citation count. Use single value (e.g., '1000') or "
                "range (e.g., '500:5000', ':1000', '1000:')",
            ),
        ] = None,
        group_by: Annotated[
            str | None,
            typer.Option(
                "--group-by",
                help="Group results by field (e.g. 'country_code', 'continent', 'type', "
                "'cited_by_count', 'works_count')",
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
                help="Sort results by field (e.g. 'cited_by_count:desc', 'works_count', "
                "'display_name:asc')",
            ),
        ] = None,
        sample: Annotated[
            int | None,
            typer.Option(
                "--sample",
                help="Get random sample of results (max 10,000). Use with --seed for "
                "reproducible results",
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
                "Example: 'id,display_name,country_code'. "
                "If not specified, returns all fields.",
            ),
        ] = None,
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
            # Validate options
            validate_pagination_options(all_results, limit)
            effective_json_path, effective_parquet_path = (
                validate_output_format_options(json_flag, json_path, parquet_path)
            )

            # Build query
            query = Institutions()

            if search:
                query = query.search(search)

            if country_code:
                query = query.filter(country_code=country_code)

            if works_count:
                parsed_works_count = parse_range_filter(works_count)
                query = apply_range_filter(query, "works_count", parsed_works_count)

            if institution_type:
                query = query.filter(type=institution_type)

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

            if cited_by_count:
                parsed_cited_by_count = parse_range_filter(cited_by_count)
                query = apply_range_filter(
                    query, "cited_by_count", parsed_cited_by_count
                )

            # Apply common options (sort, sample, select)
            query = _validate_and_apply_common_options(
                query, all_results, limit, sample, seed, sort_by, select
            )

            # Apply group_by parameter
            if group_by:
                query = query.group_by(group_by)

            # Execute query
            results = execute_standard_query(
                query, "institutions", all_results, limit, group_by
            )

            # Handle output based on query type
            if group_by:
                # Grouped results - use specialized output function
                _output_grouped_results(
                    results, effective_json_path, effective_parquet_path
                )
                return

            # Handle None results
            if results is None:
                typer.echo("No results returned from API", err=True)
                return

            _output_results(results, effective_json_path, effective_parquet_path)

        except Exception as e:
            _handle_cli_exception(e)
