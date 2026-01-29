"""Authors command for PyAlex CLI."""

from typing import Annotated

import typer

from pyalex import Authors

from ..batch import add_id_list_option_to_command
from ..command_patterns import execute_standard_query
from ..command_patterns import handle_large_id_list_if_needed
from ..command_patterns import validate_output_format_options
from ..command_patterns import validate_pagination_options
from ..constants import STDIN_SENTINEL
from ..utils import _handle_cli_exception
from ..utils import _output_grouped_results
from ..utils import _output_results
from ..utils import _validate_and_apply_common_options
from ..utils import apply_range_filter
from ..utils import parse_range_filter
from ..utils import parse_select_fields
from ..utils import resolve_ids_option
from .help_panels import AGGREGATION_PANEL
from .help_panels import ID_FILTERS_PANEL
from .help_panels import IDENTITY_PANEL
from .help_panels import METADATA_PANEL
from .help_panels import METRICS_PANEL
from .help_panels import OUTPUT_PANEL
from .help_panels import PAGINATION_PANEL
from .help_panels import RESULT_PANEL
from .help_panels import SEARCH_PANEL
from .utils import StdinSentinelCommand


def _normalize_ror_value(ror_value: str) -> str:
    """Ensure ROR identifiers include the canonical https prefix."""

    ror_value = ror_value.strip()
    if not ror_value:
        return ror_value
    if ror_value.startswith("https://ror.org/"):
        return ror_value
    if ror_value.startswith("http://ror.org/"):
        return ror_value.replace("http://", "https://", 1)
    if ror_value.startswith("ror.org/"):
        return f"https://{ror_value}"
    return f"https://ror.org/{ror_value}"


class _AuthorsCommand(StdinSentinelCommand):
    """Custom command that injects stdin sentinel for institution IDs."""

    _stdin_options = {
        "--institution-ids": STDIN_SENTINEL,
        "--institution-rors": STDIN_SENTINEL,
    }


def create_authors_command(app):
    """Create and register the authors command."""

    @app.command(cls=_AuthorsCommand, rich_help_panel="Entity Commands")
    def authors(
        search: Annotated[
            str | None,
            typer.Option(
                "--search",
                "-s",
                help="Search term for authors",
                rich_help_panel=SEARCH_PANEL,
            ),
        ] = None,
        institution_ids: Annotated[
            str | None,
            typer.Option(
                "--institution-ids",
                help=(
                    "Filter by institution OpenAlex ID(s). "
                    "Use comma-separated values for OR logic "
                    "(e.g., --institution-ids 'I123,I456,I789'). Omit the value "
                    "to read JSON input from stdin (same formats as pyalex "
                    "from-ids)"
                ),
                rich_help_panel=ID_FILTERS_PANEL,
            ),
        ] = None,
        institution_rors: Annotated[
            str | None,
            typer.Option(
                "--institution-rors",
                help=(
                    "Filter by last known institution ROR(s). Use comma-separated "
                    "values or omit the value to read JSON input from stdin with "
                    "a 'ror' field."
                ),
                rich_help_panel=ID_FILTERS_PANEL,
            ),
        ] = None,
        orcid: Annotated[
            str | None,
            typer.Option(
                "--orcid",
                help="Filter by ORCID (e.g., '0000-0002-3748-6564')",
                rich_help_panel=IDENTITY_PANEL,
            ),
        ] = None,
        has_orcid: Annotated[
            bool | None,
            typer.Option(
                "--has-orcid/--no-orcid",
                help="Filter by presence of an ORCID identifier",
                rich_help_panel=IDENTITY_PANEL,
            ),
        ] = None,
        has_twitter: Annotated[
            bool | None,
            typer.Option(
                "--has-twitter/--no-twitter",
                help="Filter by presence of a Twitter handle",
                rich_help_panel=IDENTITY_PANEL,
            ),
        ] = None,
        has_wikipedia: Annotated[
            bool | None,
            typer.Option(
                "--has-wikipedia/--no-wikipedia",
                help="Filter by presence of a Wikipedia page",
                rich_help_panel=IDENTITY_PANEL,
            ),
        ] = None,
        works_count: Annotated[
            str | None,
            typer.Option(
                "--works-count",
                help=(
                    "Filter by works count. Use single value (e.g., '100') "
                    "or range (e.g., '50:500', ':200', '100:')"
                ),
                rich_help_panel=METRICS_PANEL,
            ),
        ] = None,
        cited_by_count: Annotated[
            str | None,
            typer.Option(
                "--cited-by-count",
                help=(
                    "Filter by total citation count. Use single value "
                    "(e.g., '1000') or range (e.g., '500:5000', ':1000', '1000:')"
                ),
                rich_help_panel=METRICS_PANEL,
            ),
        ] = None,
        last_known_institution_country: Annotated[
            str | None,
            typer.Option(
                "--last-known-institution-country",
                help=(
                    "Filter by country code of last known institution "
                    "(e.g. US, UK, CA)"
                ),
                rich_help_panel=METADATA_PANEL,
            ),
        ] = None,
        h_index: Annotated[
            str | None,
            typer.Option(
                "--h-index",
                help=(
                    "Filter by h-index from summary stats. Use single value "
                    "(e.g., '50') or range (e.g., '10:100', ':50', '25:')"
                ),
                rich_help_panel=METRICS_PANEL,
            ),
        ] = None,
        i10_index: Annotated[
            str | None,
            typer.Option(
                "--i10-index",
                help=(
                    "Filter by i10-index from summary stats. Use single value "
                    "(e.g., '100') or range (e.g., '50:500', ':200', '100:')"
                ),
                rich_help_panel=METRICS_PANEL,
            ),
        ] = None,
        two_year_mean_citedness: Annotated[
            str | None,
            typer.Option(
                "--two-year-mean-citedness",
                help=(
                    "Filter by 2-year mean citedness from summary stats. Use single "
                    "value (e.g., '2.5') or range (e.g., '1.0:5.0', ':3.0', '2.0:')"
                ),
                rich_help_panel=METRICS_PANEL,
            ),
        ] = None,
        group_by: Annotated[
            str | None,
            typer.Option(
                "--group-by",
                help=(
                    "Group results by field (e.g. 'cited_by_count', 'has_orcid', "
                    "'works_count')"
                ),
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
                    "Maximum number of results to return (mutually exclusive "
                    "with --all)"
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
                    "'display_name:asc'). Multiple sorts: "
                    "'works_count:desc,cited_by_count:desc'"
                ),
                rich_help_panel=RESULT_PANEL,
            ),
        ] = None,
        sample: Annotated[
            int | None,
            typer.Option(
                "--sample",
                help=(
                    "Get random sample of results (max 10,000). "
                    "Use with --seed for reproducible results"
                ),
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
        ] = 0,
        select: Annotated[
            str | None,
            typer.Option(
                "--select",
                help=(
                    "Select specific fields to return (comma-separated). "
                    "Example: 'id,display_name,orcid'. "
                    "If not specified, returns all fields."
                ),
                rich_help_panel=RESULT_PANEL,
            ),
        ] = None,
    ):
        """
        Search and retrieve authors from OpenAlex.

        Examples:
          pyalex authors --search "John Smith"
          pyalex authors --institution-ids "I1234567890" --all
          pyalex authors --works-count "100:" --cited-by-count "1000:" --limit 50
          pyalex authors --last-known-institution-country US --h-index "25:" \
                         --jsonl-file results.jsonl
          pyalex authors --i10-index "50:" --two-year-mean-citedness "2.0:" \
                         --sort-by "cited_by_count:desc"
          pyalex authors --group-by "has_orcid"
          pyalex authors --sample 25 --seed 456
          pyalex authors --orcid "0000-0002-3748-6564"
                    pyalex authors --institution-rors "https://ror.org/01an7q238"
                    pyalex authors --has-orcid --group-by has_orcid --limit 10
        """
        try:
            # Validate options
            validate_pagination_options(all_results, limit)
            effective_jsonl_path, effective_parquet_path = (
                validate_output_format_options(
                    jsonl_flag, jsonl_path, parquet_path
                )
            )

            institution_ids = resolve_ids_option(
                institution_ids, "--institution-ids"
            )
            institution_rors = resolve_ids_option(
                institution_rors, "--institution-rors", id_field="ror"
            )

            # Build query
            query = Authors()

            if search:
                query = query.search(search)

            if institution_ids:
                query = add_id_list_option_to_command(
                    query, institution_ids, "authors_institution", Authors
                )

            if institution_rors:
                ror_values = [
                    _normalize_ror_value(value)
                    for value in institution_rors.split(",")
                    if value.strip()
                ]
                if ror_values:
                    normalized_rors = ",".join(ror_values)
                    query = add_id_list_option_to_command(
                        query,
                        normalized_rors,
                        "authors_institution_ror",
                        Authors,
                    )

            if orcid:
                query = query.filter(orcid=orcid)

            if has_orcid is not None:
                query = query.filter(has_orcid=has_orcid)

            if has_twitter is not None:
                query = query.filter(has_twitter=has_twitter)

            if has_wikipedia is not None:
                query = query.filter(has_wikipedia=has_wikipedia)

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

            cli_selected_fields = parse_select_fields(select)

            effective_sort = sort_by or "summary_stats.h_index:desc"

            query = _validate_and_apply_common_options(
                query, all_results, limit, sample, seed, effective_sort, select
            )

            if group_by:
                query = query.group_by(group_by)

            results = handle_large_id_list_if_needed(
                query,
                Authors,
                all_results,
                limit,
                effective_jsonl_path,
                group_by,
                selected_fields=cli_selected_fields,
                normalize=normalize,
            )
            if results is not None:
                return

            results = execute_standard_query(
                query, "authors", all_results, limit, group_by
            )

            if group_by:
                _output_grouped_results(
                    results,
                    effective_jsonl_path,
                    effective_parquet_path,
                    normalize=normalize,
                )
                return

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

        except typer.Exit as exc:
            raise exc
        except Exception as e:
            _handle_cli_exception(e)
