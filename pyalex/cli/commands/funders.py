"""
Funders command for PyAlex CLI.
"""

from typing import Annotated

import typer

from pyalex import Funders

from ..command_patterns import execute_standard_query
from ..command_patterns import validate_output_format_options
from ..command_patterns import validate_pagination_options
from ..utils import _handle_cli_exception
from ..utils import _output_grouped_results
from ..utils import _output_results
from ..utils import _validate_and_apply_common_options
from ..utils import apply_range_filter
from ..utils import parse_range_filter
from ..utils import parse_select_fields
from .help_panels import AGGREGATION_PANEL
from .help_panels import METADATA_PANEL
from .help_panels import METRICS_PANEL
from .help_panels import OUTPUT_PANEL
from .help_panels import PAGINATION_PANEL
from .help_panels import RESULT_PANEL
from .help_panels import SEARCH_PANEL


def create_funders_command(app):
    """Create and register the funders command."""

    @app.command(rich_help_panel="Entity Commands")
    def funders(
        search: Annotated[
            str | None,
            typer.Option(
                "--search",
                "-s",
                help="Search term for funders",
                rich_help_panel=SEARCH_PANEL,
            )
        ] = None,
        display_name_search: Annotated[
            str | None,
            typer.Option(
                "--display-name-search",
                help="Search funder display names (maps to display_name.search)",
                rich_help_panel=SEARCH_PANEL,
            ),
        ] = None,
        description_search: Annotated[
            str | None,
            typer.Option(
                "--description-search",
                help="Search funder descriptions (maps to description.search)",
                rich_help_panel=SEARCH_PANEL,
            ),
        ] = None,
        country_code: Annotated[
            str | None,
            typer.Option(
                "--country",
                help="Filter by country code (e.g. US, UK, CA)",
                rich_help_panel=METADATA_PANEL,
            ),
        ] = None,
        grants_count: Annotated[
            str | None,
            typer.Option(
                "--grants-count",
                help="Filter by grants count. Use single value (e.g., '100') or "
                "range (e.g., '50:500', ':200', '100:')",
                rich_help_panel=METRICS_PANEL,
            ),
        ] = None,
        works_count: Annotated[
            str | None,
            typer.Option(
                "--works-count",
                help="Filter by works count. Use single value (e.g., '1000') or "
                "range (e.g., '100:5000', ':1000', '500:')",
                rich_help_panel=METRICS_PANEL,
            ),
        ] = None,
        h_index: Annotated[
            str | None,
            typer.Option(
                "--h-index",
                help=(
                    "Filter by h-index from summary stats. "
                    "Use single value (e.g., '50') "
                    "or range (e.g., '10:100', ':50', '25:')"
                ),
                rich_help_panel=METRICS_PANEL,
            ),
        ] = None,
        i10_index: Annotated[
            str | None,
            typer.Option(
                "--i10-index",
                help="Filter by i10-index from summary stats. Use single value "
                "(e.g., '100') or range (e.g., '50:500', ':200', '100:')",
                rich_help_panel=METRICS_PANEL,
            ),
        ] = None,
        two_year_mean_citedness: Annotated[
            str | None,
            typer.Option(
                "--two-year-mean-citedness",
                help=(
                    "Filter by 2-year mean citedness from summary stats. "
                    "Use single value (e.g., '2.5') "
                    "or range (e.g., '1.0:5.0', ':3.0', '2.0:')"
                ),
                rich_help_panel=METRICS_PANEL,
            ),
        ] = None,
        group_by: Annotated[
            str | None,
            typer.Option(
                "--group-by",
                help="Group results by field (e.g. 'country_code', 'works_count')",
                rich_help_panel=AGGREGATION_PANEL,
            ),
        ] = None,
        all_results: Annotated[
            bool,
            typer.Option(
                "--all",
                help="Retrieve all results (default: first page only)",
                rich_help_panel=PAGINATION_PANEL,
            ),
        ] = False,
        limit: Annotated[
            int | None,
            typer.Option(
                "--limit",
                "-l",
                help=(
                    "Maximum number of results to return "
                    "(mutually exclusive with --all)"
                ),
                rich_help_panel=PAGINATION_PANEL,
            ),
        ] = None,
        jsonl_flag: Annotated[
            bool,
            typer.Option(
                "--jsonl",
                help="Output JSON Lines to stdout",
                rich_help_panel=OUTPUT_PANEL,
            )
        ] = False,
        jsonl_path: Annotated[
            str | None,
            typer.Option(
                "--jsonl-file",
                help="Save results to JSON Lines file at specified path",
                rich_help_panel=OUTPUT_PANEL,
            ),
        ] = None,
        parquet_path: Annotated[
            str | None,
            typer.Option(
                "--parquet-file",
                help="Save results to Parquet file at specified path",
                rich_help_panel=OUTPUT_PANEL,
            ),
        ] = None,
        normalize: Annotated[
            bool,
            typer.Option(
                "--normalize",
                help=(
                    "Flatten nested fields using pandas.json_normalize before "
                    "emitting results"
                ),
                rich_help_panel=OUTPUT_PANEL,
            ),
        ] = False,
        sort_by: Annotated[
            str | None,
            typer.Option(
                "--sort-by",
                help=(
                    "Sort results by field (e.g. 'cited_by_count:desc', 'works_count', "
                    "'display_name:asc')"
                ),
                rich_help_panel=RESULT_PANEL,
            ),
        ] = None,
        sample: Annotated[
            int | None,
            typer.Option(
                "--sample",
                help="Get random sample of results (max 10,000). Use with --seed for "
                "reproducible results",
                rich_help_panel=RESULT_PANEL,
            ),
        ] = None,
        seed: Annotated[
            int | None,
            typer.Option(
                "--seed",
                help="Seed for random sampling (used with --sample)",
                rich_help_panel=RESULT_PANEL,
            ),
        ] = None,
        select: Annotated[
            str | None,
            typer.Option(
                "--select",
                help="Select specific fields to return (comma-separated). "
                "Example: 'id,display_name,country_code'. "
                "If not specified, returns all fields.",
                rich_help_panel=RESULT_PANEL,
            ),
        ] = None,
    ):
        """
        Search and retrieve funders from OpenAlex.
        
        Examples:
          pyalex funders --search "NSF"
                    pyalex funders --display-name-search "National Science"
          pyalex funders --country US --all
          pyalex funders --works-count "1000:10000" --limit 50
          pyalex funders --grants-count "50:" --h-index "25:" \
                         --jsonl-file results.jsonl
          pyalex funders --country US --two-year-mean-citedness "2.0:" \\
                         --sort-by "works_count:desc"
          pyalex funders --group-by "country_code"
          pyalex funders --sample 10 --seed 404
        """
        try:
            # Validate options
            validate_pagination_options(all_results, limit)
            effective_jsonl_path, effective_parquet_path = (
                validate_output_format_options(
                    jsonl_flag, jsonl_path, parquet_path
                )
            )

            # Build query
            query = Funders()

            if search:
                query = query.search(search)

            if display_name_search:
                query = query.search_filter(display_name=display_name_search)

            if description_search:
                query = query.search_filter(description=description_search)

            if country_code:
                query = query.filter(country_code=country_code)

            if grants_count:
                parsed_grants_count = parse_range_filter(grants_count)
                query = apply_range_filter(query, "grants_count", parsed_grants_count)

            if works_count:
                parsed_works_count = parse_range_filter(works_count)
                query = apply_range_filter(query, "works_count", parsed_works_count)

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

            cli_selected_fields = parse_select_fields(select)

            # Apply common options (sort, sample, select)
            query = _validate_and_apply_common_options(
                query, all_results, limit, sample, seed, sort_by, select
            )

            # Apply group_by parameter
            if group_by:
                query = query.group_by(group_by)

            # Execute query
            results = execute_standard_query(
                query, "funders", all_results, limit, group_by
            )

            # Handle output based on query type
            if group_by:
                # Grouped results - use specialized output function
                _output_grouped_results(
                    results,
                    effective_jsonl_path,
                    effective_parquet_path,
                    normalize=normalize,
                )
                return

            # Handle None results
            if results is None:
                typer.echo("No results returned from API", err=True)
                return

            _output_results(
                results,
                effective_jsonl_path,
                effective_parquet_path,
                selected_fields=cli_selected_fields,
                normalize=normalize,
            )

        except Exception as e:
            _handle_cli_exception(e)
