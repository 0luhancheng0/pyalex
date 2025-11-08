"""
Simple entity commands template for PyAlex CLI.

This module contains basic implementations for entity commands
that follow a common pattern.
"""

import asyncio
from typing import Annotated

import typer

from pyalex import Concepts
from pyalex import Domains
from pyalex import Fields
from pyalex import Keywords
from pyalex import Publishers
from pyalex import Sources
from pyalex import Subfields
from pyalex import Topics

from ..utils import _dry_run_mode
from ..utils import _handle_cli_exception
from ..utils import _output_grouped_results
from ..utils import _output_results
from ..utils import _paginate_with_progress
from ..utils import _print_debug_results
from ..utils import _print_debug_url
from ..utils import _print_dry_run_query
from ..utils import _validate_and_apply_common_options
from ..utils import parse_select_fields


def create_simple_entity_command(app, entity_class, entity_name, entity_name_lower):
    """Create a simple entity command with standard options."""

    def command_func(
        search: Annotated[
            str | None,
            typer.Option("--search", "-s", help=f"Search term for {entity_name_lower}"),
        ] = None,
        group_by: Annotated[
            str | None, typer.Option("--group-by", help="Group results by field")
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
                help=(
                    "Maximum number of results to return "
                    "(mutually exclusive with --all)"
                ),
            ),
        ] = None,
        jsonl_flag: Annotated[
            bool, typer.Option("--jsonl", help="Output JSON Lines to stdout")
        ] = False,
        jsonl_path: Annotated[
            str | None,
            typer.Option(
                "--jsonl-file",
                help="Save results to JSON Lines file at specified path",
            ),
        ] = None,
        parquet_path: Annotated[
            str | None,
            typer.Option(
                "--parquet-file",
                help="Save results to Parquet file at specified path",
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
                ),
            ] = False,
        sort_by: Annotated[
            str | None, typer.Option("--sort-by", help="Sort results by field")
        ] = None,
        sample: Annotated[
            int | None,
            typer.Option("--sample", help="Get random sample of results (max 10,000)"),
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
                "--select", help="Select specific fields to return (comma-separated)"
            ),
        ] = None,
    ):
        """
        Search and retrieve {entity_name_lower} from OpenAlex.

        Examples:
          pyalex {entity_name_lower} --search "example"
          pyalex {entity_name_lower} --all
          pyalex {entity_name_lower} --limit 50 --jsonl-file results.jsonl
        """
        try:
            # Check for mutually exclusive options
            if all_results and limit is not None:
                typer.echo("Error: --all and --limit are mutually exclusive", err=True)
                raise typer.Exit(1)

            # Handle output format options - check mutual exclusivity
            options_provided = sum(
                [jsonl_flag, jsonl_path is not None, parquet_path is not None]
            )

            if options_provided > 1:
                typer.echo(
                    "Error: --jsonl, --jsonl-file, and --parquet-file "
                    "are mutually exclusive",
                    err=True,
                )
                raise typer.Exit(1)

            # Resolve JSON path
            effective_jsonl_path = None
            if jsonl_flag:
                effective_jsonl_path = "-"  # stdout
            elif jsonl_path:
                effective_jsonl_path = jsonl_path

            effective_parquet_path = parquet_path

            # Create query
            query = entity_class()

            if search:
                query = query.search(search)

            cli_selected_fields = parse_select_fields(select)

            # Apply common options
            query = _validate_and_apply_common_options(
                query, all_results, limit, sample, seed, sort_by, select
            )

            # Handle group_by parameter
            if group_by:
                query = query.group_by(group_by)
                _print_debug_url(query)

                # For group-by operations, only page 1 is supported (max 200 results)
                results = asyncio.run(query.get(per_page=200))
                _print_debug_results(results)
                _output_grouped_results(
                    results,
                    effective_jsonl_path,
                    effective_parquet_path,
                    normalize=normalize,
                )
                return

            _print_debug_url(query)

            if _dry_run_mode:
                _print_dry_run_query(f"{entity_name} query", url=query.url)
                return

            if all_results:
                # Get all results using pagination with progress bar
                results = _paginate_with_progress(query, entity_name_lower)
            elif limit is not None:
                results = asyncio.run(query.get(limit=limit))
            else:
                results = asyncio.run(query.get())  # Default first page

            _print_debug_results(results)
            _output_results(
                results,
                effective_jsonl_path,
                effective_parquet_path,
                    selected_fields=cli_selected_fields,
                    normalize=normalize,
            )

        except Exception as e:
            _handle_cli_exception(e)

    # Set proper function name and docstring
    command_func.__name__ = entity_name_lower
    return command_func


def create_entity_commands(app):
    """Create and register all simple entity commands."""

    # Concepts
    concepts_func = create_simple_entity_command(
        app, Concepts, "Concepts", "concepts"
    )
    app.command(help="Search and retrieve concepts from OpenAlex")(concepts_func)

    # Topics
    topics_func = create_simple_entity_command(app, Topics, "Topics", "topics")
    app.command(help="Search and retrieve topics from OpenAlex")(topics_func)

    # Sources
    sources_func = create_simple_entity_command(app, Sources, "Sources", "sources")
    app.command(help="Search and retrieve sources (journals/venues) from OpenAlex")(
        sources_func
    )

    # Publishers
    publishers_func = create_simple_entity_command(
        app, Publishers, "Publishers", "publishers"
    )
    app.command(help="Search and retrieve publishers from OpenAlex")(publishers_func)

    # Domains
    domains_func = create_simple_entity_command(app, Domains, "Domains", "domains")
    app.command(help="Search and retrieve domains from OpenAlex")(domains_func)

    # Fields
    fields_func = create_simple_entity_command(app, Fields, "Fields", "fields")
    app.command(help="Search and retrieve fields from OpenAlex")(fields_func)

    # Subfields
    subfields_func = create_simple_entity_command(
        app, Subfields, "Subfields", "subfields"
    )
    app.command(help="Search and retrieve subfields from OpenAlex")(subfields_func)

    # Keywords
    keywords_func = create_simple_entity_command(app, Keywords, "Keywords", "keywords")
    app.command(help="Search and retrieve keywords from OpenAlex")(keywords_func)
