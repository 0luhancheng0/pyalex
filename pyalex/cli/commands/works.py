"""Works command for PyAlex CLI."""

import datetime
import re
from typing import Annotated

import typer

from pyalex import Works

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
from .help_panels import ACCESS_PANEL
from .help_panels import AGGREGATION_PANEL
from .help_panels import ID_FILTERS_PANEL
from .help_panels import METADATA_PANEL
from .help_panels import METRICS_PANEL
from .help_panels import OUTPUT_PANEL
from .help_panels import PAGINATION_PANEL
from .help_panels import RESULT_PANEL
from .help_panels import SEARCH_PANEL
from .utils import StdinSentinelCommand


class _WorksCommand(StdinSentinelCommand):
    """Custom command that injects stdin sentinels for ID options."""

    _stdin_options = {
        "--author-ids": STDIN_SENTINEL,
        "--institution-ids": STDIN_SENTINEL,
        "--institutions-country-code": STDIN_SENTINEL,
        "--topic-ids": STDIN_SENTINEL,
        "--subfield-ids": STDIN_SENTINEL,
        "--funder-ids": STDIN_SENTINEL,
        "--award-ids": STDIN_SENTINEL,
        "--source-ids": STDIN_SENTINEL,
        "--host-venue-ids": STDIN_SENTINEL,
        "--source-issn": STDIN_SENTINEL,
        "--source-host-org-ids": STDIN_SENTINEL,
        "--cites": STDIN_SENTINEL,
    }


def _apply_citation_percentile_value_filter(query, raw_value: str):
    """Apply citation_normalized_percentile.value filters to the query."""

    value = (raw_value or "").strip()
    if not value:
        raise ValueError("Citation percentile value cannot be empty")

    def _parse_numeric(fragment: str) -> float:
        try:
            return float(fragment)
        except ValueError as exc:
            raise ValueError(
                "Invalid citation percentile value; provide a numeric input"
            ) from exc

    if ":" in value:
        start_str, end_str = value.split(":", 1)
        start_str = start_str.strip()
        end_str = end_str.strip()

        if not start_str and not end_str:
            raise ValueError("Citation percentile range must include a bound")

        if start_str:
            start_val = _parse_numeric(start_str)
            query = query.filter_gt(
                citation_normalized_percentile={"value": start_val}
            )

        if end_str:
            end_val = _parse_numeric(end_str)
            if start_str and start_val > end_val:
                raise ValueError(
                    "Citation percentile start value must not exceed end value"
                )
            query = query.filter_lt(
                citation_normalized_percentile={"value": end_val}
            )

        return query

    if value.startswith((">", "<")):
        operator = value[0]
        remainder = value[1:].strip()
        if not remainder:
            raise ValueError(
                "Comparison citation percentile value requires a numeric bound"
            )
        numeric_value = _parse_numeric(remainder)
        if operator == ">":
            return query.filter_gt(
                citation_normalized_percentile={"value": numeric_value}
            )

        return query.filter_lt(
            citation_normalized_percentile={"value": numeric_value}
        )

    exact_value = _parse_numeric(value)
    return query.filter(citation_normalized_percentile={"value": exact_value})


def create_works_command(app):
    """Create and register the works command."""

    @app.command(cls=_WorksCommand, rich_help_panel="Entity Commands")
    def works(
        search: Annotated[
            str | None,
            typer.Option(
                "--search",
                "-s",
                help="Search term for works",
                rich_help_panel=SEARCH_PANEL,
            ),
        ] = None,
        title_search: Annotated[
            str | None,
            typer.Option(
                "--title-search",
                "--display-name-search",
                help="Search within work titles (maps to title.search)",
                rich_help_panel=SEARCH_PANEL,
            ),
        ] = None,
        abstract_search: Annotated[
            str | None,
            typer.Option(
                "--abstract-search",
                help="Search within the inverted abstract (maps to abstract.search)",
                rich_help_panel=SEARCH_PANEL,
            ),
        ] = None,
        title_and_abstract_search: Annotated[
            str | None,
            typer.Option(
                "--title-and-abstract-search",
                help=(
                    "Search across titles and abstracts together "
                    "(maps to title_and_abstract.search)"
                ),
                rich_help_panel=SEARCH_PANEL,
            ),
        ] = None,
        fulltext_search: Annotated[
            str | None,
            typer.Option(
                "--fulltext-search",
                help="Search fulltext n-grams (maps to fulltext.search)",
                rich_help_panel=SEARCH_PANEL,
            ),
        ] = None,
        raw_affiliation_search: Annotated[
            str | None,
            typer.Option(
                "--raw-affiliation-search",
                help=(
                    "Search raw affiliation strings from authorships "
                    "(maps to raw_affiliation_strings.search)"
                ),
                rich_help_panel=SEARCH_PANEL,
            ),
        ] = None,
        author_ids: Annotated[
            str | None,
            typer.Option(
                "--author-ids",
                help=(
                    "Filter by author OpenAlex ID(s). Use comma-separated values for "
                    "OR logic (e.g., --author-ids 'A123,A456,A789'). Omit the value "
                    "to read JSON input from stdin (same formats as pyalex from-ids)"
                ),
                rich_help_panel=ID_FILTERS_PANEL,
            ),
        ] = None,
        institution_ids: Annotated[
            str | None,
            typer.Option(
                "--institution-ids",
                help=(
                    "Filter by institution OpenAlex ID(s). Use comma-separated values "
                    "for OR logic (e.g., --institution-ids 'I123,I456,I789'). Omit "
                    "the value to read JSON input from stdin (same formats as pyalex "
                    "from-ids)"
                ),
                rich_help_panel=ID_FILTERS_PANEL,
            ),
        ] = None,
        institutions_country_code: Annotated[
            str | None,
            typer.Option(
                "--institutions-country-code",
                help=(
                    "Filter by institution country code(s) (ISO 3166-1 alpha-2). "
                    "Use comma-separated values for OR logic (e.g., 'fr,gb'). "
                    "Omit the value to read from stdin."
                ),
                rich_help_panel=ID_FILTERS_PANEL,
            ),
        ] = None,
        publication_year: Annotated[
            str | None,
            typer.Option(
                "--year",
                help="Filter by publication year (e.g. '2020' or range '2019:2021')",
                rich_help_panel=METADATA_PANEL,
            ),
        ] = None,
        publication_date: Annotated[
            str | None,
            typer.Option(
                "--date",
                help="Filter by publication date (e.g. '2020-01-01' or "
                "range '2019-01-01:2020-12-31')",
                rich_help_panel=METADATA_PANEL,
            ),
        ] = None,
        work_type: Annotated[
            str | None,
            typer.Option(
                "--type",
                help="Filter by work type (e.g. 'article', 'book', 'dataset')",
                rich_help_panel=METADATA_PANEL,
            ),
        ] = None,
        topic_ids: Annotated[
            str | None,
            typer.Option(
                "--topic-ids",
                help=(
                    "Filter by primary topic OpenAlex ID(s). "
                    "Use comma-separated values for OR logic "
                    "(e.g., --topic-ids 'T123,T456,T789'). Omit the value to read "
                    "JSON input from stdin (same formats as pyalex from-ids)"
                ),
                rich_help_panel=ID_FILTERS_PANEL,
            ),
        ] = None,
        subfield_ids: Annotated[
            str | None,
            typer.Option(
                "--subfield-ids",
                help=(
                    "Filter by primary topic subfield OpenAlex ID(s). Use "
                    "comma-separated values for OR logic (e.g., --subfield-ids "
                    "'SF123,SF456,SF789'). Omit the value to read JSON input from "
                    "stdin (same formats as pyalex from-ids)"
                ),
                rich_help_panel=ID_FILTERS_PANEL,
            ),
        ] = None,
        funder_ids: Annotated[
            str | None,
            typer.Option(
                "--funder-ids",
                help="Filter by funder OpenAlex ID(s). Use comma-separated values for "
                "OR logic (e.g., --funder-ids 'F123,F456,F789'). Omit the value to "
                "read JSON input from stdin (same formats as pyalex from-ids)",
                metavar="ID[,ID...]",
                rich_help_panel=ID_FILTERS_PANEL,
            ),
        ] = None,
        award_ids: Annotated[
            str | None,
            typer.Option(
                "--award-ids",
                help=(
                    "Filter by grant award ID(s). Use comma-separated values for "
                    "OR logic (e.g., --award-ids 'AWARD123,AWARD456'). Omit the "
                    "value to read JSON input from stdin (same formats as pyalex "
                    "from-ids)"
                ),
                rich_help_panel=ID_FILTERS_PANEL,
            ),
        ] = None,
        source_ids: Annotated[
            str | None,
            typer.Option(
                "--source-ids",
                help=(
                    "Filter by primary source OpenAlex ID(s). Use comma-separated "
                    "values for OR logic (e.g., --source-ids 'S123,S456'). Omit "
                    "the value to read JSON input from stdin."
                ),
                metavar="ID[,ID...]",
                rich_help_panel=ID_FILTERS_PANEL,
            ),
        ] = None,
        host_venue_ids: Annotated[
            str | None,
            typer.Option(
                "--host-venue-ids",
                help=(
                    "Filter by host venue OpenAlex ID(s). Use comma-separated "
                    "values for OR logic (e.g., --host-venue-ids 'S123,S456'). "
                    "Omit the value to read JSON input from stdin."
                ),
                metavar="ID[,ID...]",
                rich_help_panel=ID_FILTERS_PANEL,
            ),
        ] = None,
        source_issn: Annotated[
            str | None,
            typer.Option(
                "--source-issn",
                help=(
                    "Filter by source ISSN. Accepts comma-separated values or "
                    "JSON input from stdin with an 'issn' field."
                ),
                metavar="ISSN[,ISSN...]",
                rich_help_panel=ID_FILTERS_PANEL,
            ),
        ] = None,
        source_host_org_ids: Annotated[
            str | None,
            typer.Option(
                "--source-host-org-ids",
                help=(
                    "Filter by source host organization (publisher) OpenAlex ID(s). "
                    "Use comma-separated values for OR logic or supply JSON via stdin."
                ),
                metavar="ID[,ID...]",
                rich_help_panel=ID_FILTERS_PANEL,
            ),
        ] = None,
        cited_by_count: Annotated[
            str | None,
            typer.Option(
                "--cited-by-count",
                help=(
                    "Filter by total citation count. Use single value (e.g., '1000') "
                    "or range (e.g., '500:5000', ':1000', '1000:')"
                ),
                rich_help_panel=METRICS_PANEL,
            ),
        ] = None,
        citation_percentile_top_1: Annotated[
            bool | None,
            typer.Option(
                "--citation-percentile-top-1/--no-citation-percentile-top-1",
                help=(
                    "Filter by citation_normalized_percentile.is_in_top_1_percent"
                ),
                rich_help_panel=METRICS_PANEL,
            ),
        ] = None,
        citation_percentile_top_10: Annotated[
            bool | None,
            typer.Option(
                "--citation-percentile-top-10/--no-citation-percentile-top-10",
                help=(
                    "Filter by citation_normalized_percentile.is_in_top_10_percent"
                ),
                rich_help_panel=METRICS_PANEL,
            ),
        ] = None,
        citation_percentile_value: Annotated[
            str | None,
            typer.Option(
                "--citation-percentile-value",
                help=(
                    "Filter by citation_normalized_percentile.value. Accepts "
                    "single values (e.g., '0.95'), ranges ('0.9:1.0'), or "
                    "comparisons ('>0.9', '<0.5')."
                ),
                rich_help_panel=METRICS_PANEL,
            ),
        ] = None,
        cited_by_ids: Annotated[
            str | None,
            typer.Option(
                "--cites",
                help=(
                    "Filter works cited by the provided work ID(s). Use "
                    "comma-separated IDs or omit the value to read JSON from stdin."
                ),
                rich_help_panel=ID_FILTERS_PANEL,
            ),
        ] = None,
        is_oa: Annotated[
            bool | None,
            typer.Option(
                "--is-oa/--not-oa",
                help="Filter by open access availability (default: no filter)",
                rich_help_panel=ACCESS_PANEL,
            ),
        ] = None,
        oa_status: Annotated[
            str | None,
            typer.Option(
                "--oa-status",
                help=(
                    "Filter by specific OA status. Supports ranges (e.g. 'green:', ':gold'). "
                    "Ranking: diamond > gold > green > hybrid > bronze > closed"
                ),
                rich_help_panel=ACCESS_PANEL,
            ),
        ] = None,
        has_fulltext: Annotated[
            bool | None,
            typer.Option(
                "--has-fulltext/--no-fulltext",
                help="Filter by availability of any fulltext link",
                rich_help_panel=ACCESS_PANEL,
            ),
        ] = None,
        is_retracted: Annotated[
            bool | None,
            typer.Option(
                "--is-retracted/--not-retracted",
                help="Filter by retracted status",
                rich_help_panel=ACCESS_PANEL,
            ),
        ] = None,
        group_by: Annotated[
            str | None,
            typer.Option(
                "--group-by",
                help="Group results by field (e.g. 'oa_status', 'publication_year', "
                "'type', 'is_retracted', 'cited_by_count')",
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
            ),
        ] = False,
        jsonl_path: Annotated[
            str | None,
            typer.Option(
                "--jsonl-file",
                help="Save results to JSON Lines file at specified path",
                rich_help_panel=OUTPUT_PANEL,
            ),
        ] = None,
        output_path: Annotated[
            str | None,
            typer.Option(
                "--output",
                "-o",
                help="Output file path (extension determines format: .jsonl)",
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
                    "Sort results by field (e.g. 'cited_by_count:desc', "
                    "'publication_year', 'display_name:asc'). Multiple sorts: "
                    "'year:desc,cited_by_count:desc'"
                ),
                rich_help_panel=RESULT_PANEL,
            ),
        ] = None,
        sample: Annotated[
            int | None,
            typer.Option(
                "--sample",
                help="Get random sample of results (max 10,000). "
                "Use with --seed for reproducible results",
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
                help="Select specific fields to return (comma-separated). "
                "Example: 'id,doi,title,display_name'. "
                "If not specified, returns all fields.",
                rich_help_panel=RESULT_PANEL,
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
          pyalex works --citation-percentile-top-1
          pyalex works --citation-percentile-value "0.95:1.0"
          cat funders.json | pyalex works --funder-ids --limit 10
          pyalex works --award-ids "AWARD123,AWARD456"
          pyalex works --cites "W123,W456" --limit 10
          pyalex works --source-issn "2167-8359"
          pyalex works --host-venue-ids "S1983995261"
          pyalex works --is-oa --has-fulltext --abstract-search "machine vision"
          pyalex works --is-retracted --limit 20
          pyalex works --search "AI" --json ai_works.json
          pyalex works --group-by "oa_status"
          pyalex works --group-by "publication_year" --search "COVID-19"
          pyalex works --sort-by "cited_by_count:desc" --limit 100
          pyalex works --sample 50 --seed 123
          pyalex works --search "climate change" \\
            --sort-by "publication_year:desc,cited_by_count:desc"
                        pyalex works --title-search "graphene" --limit 25
                        pyalex works --fulltext-search "quantum computing"
        """
        try:
            # Validate options
            validate_pagination_options(all_results, limit)
            effective_jsonl_path = validate_output_format_options(
                jsonl_flag, jsonl_path, output_path
            )

            author_ids = resolve_ids_option(author_ids, "--author-ids")
            institution_ids = resolve_ids_option(
                institution_ids, "--institution-ids"
            )
            institutions_country_code = resolve_ids_option(
                institutions_country_code, "--institutions-country-code"
            )
            topic_ids = resolve_ids_option(topic_ids, "--topic-ids")
            subfield_ids = resolve_ids_option(subfield_ids, "--subfield-ids")
            funder_ids = resolve_ids_option(funder_ids, "--funder-ids")
            award_ids = resolve_ids_option(award_ids, "--award-ids")
            source_ids = resolve_ids_option(source_ids, "--source-ids")
            host_venue_ids = resolve_ids_option(
                host_venue_ids, "--host-venue-ids"
            )
            source_issn = resolve_ids_option(
                source_issn, "--source-issn", id_field="issn"
            )
            source_host_org_ids = resolve_ids_option(
                source_host_org_ids, "--source-host-org-ids"
            )
            cited_by_ids = resolve_ids_option(cited_by_ids, "--cited-by")

            # Build query
            query = Works()

            if search:
                query = query.search(search)

            if title_search:
                query = query.search_filter(title=title_search)

            if abstract_search:
                query = query.search_filter(abstract=abstract_search)

            if title_and_abstract_search:
                query = query.search_filter(
                    title_and_abstract=title_and_abstract_search
                )

            if fulltext_search:
                query = query.search_filter(fulltext=fulltext_search)

            if raw_affiliation_search:
                query = query.search_filter(
                    raw_affiliation_strings=raw_affiliation_search
                )

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

            if institutions_country_code:
                query = add_id_list_option_to_command(
                    query,
                    institutions_country_code,
                    "works_institutions_country_code",
                    Works,
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

                        # Handle relative start date (e.g. "-7d")
                        if re.match(r"^-\d+d$", start_date):
                            days_ago = int(start_date[1:-1])
                            start_date = (
                                datetime.date.today()
                                - datetime.timedelta(days=days_ago)
                            ).strftime("%Y-%m-%d")

                            # If end date is missing for relative range, default to today
                            if not end_date:
                                end_date = datetime.date.today().strftime("%Y-%m-%d")

                        # Validate date format (basic check for YYYY-MM-DD)
                        datetime.datetime.strptime(start_date, "%Y-%m-%d")
                        datetime.datetime.strptime(end_date, "%Y-%m-%d")

                        query = query.filter_by_publication_date(
                            start_date=start_date, end_date=end_date
                        )
                    except ValueError as ve:
                        typer.echo(
                            "Error: Invalid date range format. Use "
                            "'YYYY-MM-DD:YYYY-MM-DD' (e.g., '2019-01-01:2020-12-31') "
                            "or relative format (e.g., '-7d:')",
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

            if source_ids:
                query = add_id_list_option_to_command(
                    query, source_ids, "works_source", Works
                )

            if host_venue_ids:
                query = add_id_list_option_to_command(
                    query, host_venue_ids, "works_host_venue", Works
                )

            if source_issn:
                query = add_id_list_option_to_command(
                    query, source_issn, "works_source_issn", Works
                )

            if source_host_org_ids:
                query = add_id_list_option_to_command(
                    query, source_host_org_ids, "works_source_host_org", Works
                )

            if cited_by_count:
                parsed_cited_by_count = parse_range_filter(cited_by_count)
                query = apply_range_filter(
                    query, "cited_by_count", parsed_cited_by_count
                )

            if citation_percentile_top_1 is not None:
                query = query.filter(
                    citation_normalized_percentile={
                        "is_in_top_1_percent": citation_percentile_top_1
                    }
                )

            if citation_percentile_top_10 is not None:
                query = query.filter(
                    citation_normalized_percentile={
                        "is_in_top_10_percent": citation_percentile_top_10
                    }
                )

            if citation_percentile_value:
                try:
                    query = _apply_citation_percentile_value_filter(
                        query, citation_percentile_value
                    )
                except ValueError as exc:
                    typer.echo(f"Error: {exc}", err=True)
                    raise typer.Exit(1) from exc

            if cited_by_ids:
                query = add_id_list_option_to_command(
                    query, cited_by_ids, "works_cites", Works
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

            if oa_status:
                # Handle OA status hierarchy ranges
                # Ranking from lowest (closed) to highest (diamond) openness
                oa_ranks = ["closed", "bronze", "hybrid", "green", "gold", "diamond"]
                
                if ":" in oa_status:
                    start_stat, end_stat = oa_status.split(":", 1)
                    start_stat = start_stat.strip().lower()
                    end_stat = end_stat.strip().lower()
                    
                    start_idx = 0
                    end_idx = len(oa_ranks) - 1
                    
                    if start_stat:
                        if start_stat not in oa_ranks:
                             typer.echo(
                                 f"Error: Invalid OA status '{start_stat}'. "
                                 f"Valid statuses: {', '.join(oa_ranks)}", 
                                 err=True
                             )
                             raise typer.Exit(1)
                        start_idx = oa_ranks.index(start_stat)
                    
                    if end_stat:
                        if end_stat not in oa_ranks:
                             typer.echo(
                                 f"Error: Invalid OA status '{end_stat}'. "
                                 f"Valid statuses: {', '.join(oa_ranks)}", 
                                 err=True
                             )
                             raise typer.Exit(1)
                        end_idx = oa_ranks.index(end_stat)
                    
                    if start_idx > end_idx:
                         typer.echo("Error: Start status rank is higher than end status.", err=True)
                         raise typer.Exit(1)
                         
                    # Join selected statuses with OR operator (|)
                    selected_stats = oa_ranks[start_idx : end_idx + 1]
                    oa_status = "|".join(selected_stats)

                query = query.filter_by_open_access(oa_status=oa_status)
            elif is_oa is not None:
                query = query.filter_by_open_access(is_oa=is_oa)

            if has_fulltext is not None:
                query = query.filter(has_fulltext=has_fulltext)

            if is_retracted is not None:
                query = query.filter(is_retracted=is_retracted)

            # Apply common options (sort, sample, select)
            cli_selected_fields = parse_select_fields(select)

            select_for_query = select
            if cli_selected_fields:
                normalized_fields = [
                    field.lower() for field in cli_selected_fields if field != "id"
                ]

                needs_abstract_text = any(
                    field == "abstract" or field.startswith("abstract.")
                    for field in normalized_fields
                )

                if needs_abstract_text and select:
                    raw_select_fields = [
                        field.strip() for field in select.split(",") if field.strip()
                    ]

                    sanitized_fields = [
                        field
                        for field in raw_select_fields
                        if field.lower() not in {"abstract"}
                    ]
                    lower_sanitized = {
                        field.lower() for field in sanitized_fields
                    }
                    if "abstract_inverted_index" not in lower_sanitized:
                        sanitized_fields.append("abstract_inverted_index")
                    select_for_query = ",".join(sanitized_fields)

            query = _validate_and_apply_common_options(
                query, all_results, limit, sample, seed, sort_by, select_for_query
            )

            # Apply group_by parameter
            if group_by:
                query = query.group_by(group_by)

            # Check for and handle large ID lists (batch processing)
            results = handle_large_id_list_if_needed(
                query,
                Works,
                all_results,
                limit,
                effective_jsonl_path,
                group_by,
                selected_fields=cli_selected_fields,
                normalize=normalize,
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
                    results,
                    effective_jsonl_path,
                    normalize=normalize,
                )
                return

            # Handle None or empty results
            if results is None:
                typer.echo("No results returned from API", err=True)
                return

            # Abstract conversion now happens automatically in _output_results
            _output_results(
                results,
                effective_jsonl_path,
                selected_fields=cli_selected_fields,
                normalize=normalize,
            )

        except typer.Exit as exc:
            raise exc
        except Exception as e:
            _handle_cli_exception(e)
