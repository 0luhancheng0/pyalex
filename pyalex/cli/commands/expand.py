"""
Expand command for PyAlex CLI.

Unified command to expand works by fetching related, referenced, or citing works.
"""

import asyncio
import json
from enum import Enum
from typing import Annotated
from typing import Optional

import typer

from pyalex import Authors
from pyalex import Institutions
from pyalex import Works

from ..batch import add_id_list_option_to_command
from ..command_patterns import execute_standard_query
from ..command_patterns import handle_large_id_list_if_needed
from ..command_patterns import validate_output_format_options
from ..utils import _async_retrieve_entities
from ..utils import _handle_cli_exception
from ..utils import _output_results
from .help_panels import OUTPUT_PANEL


class ExpandMode(str, Enum):
    work_related = "work_related"
    work_forward = "work_forward"
    work_backward = "work_backward"
    work_authors = "work_authors"
    work_institutions = "work_institutions"
    author_institutions = "author_institutions"
    author_works = "author_works"


def expand(
    input_path: Annotated[
        Optional[str],
        typer.Argument(
            help="Path to input JSONL file containing Works or Authors",
        ),
    ] = None,
    input_opt: Annotated[
        Optional[str],
        typer.Option(
            "--input",
            "-i",
            help="Path to input JSONL file containing Works or Authors",
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
    mode: Annotated[
        ExpandMode,
        typer.Option(
            "--mode",
            "-m",
            help="Expansion mode: 'work_related' (related_works), 'work_backward' (referenced_works), 'work_forward' (citing works), 'work_authors' (authors of the input works), 'work_institutions' (institutions of the input works), 'author_institutions' (institutions of the input authors), or 'author_works' (works of the input authors)",
        ),
    ] = ExpandMode.work_related,
    jsonl_flag: Annotated[
        bool,
        typer.Option(
            "--jsonl",
            help="Output JSON Lines to stdout",
            rich_help_panel=OUTPUT_PANEL,
        ),
    ] = False,
    # Legacy output options for compatibility with validate_output_format_options check
    # We can probably omit them if we update the validator, but validator expects them?
    # No, validator takes arguments. We can pass None if we don't expose them.
    # But if we want to be helpful, we can expose --jsonl-file as hidden or just don't default it.
    # Plan said remove --jsonl-file. So I won't include it.
    normalize: Annotated[
        bool,
        typer.Option(
            "--normalize",
            help="Flatten nested fields using pandas.json_normalize before emitting results",
            rich_help_panel=OUTPUT_PANEL,
        ),
    ] = False,
):
    """
    Expand a set of Works or Authors by fetching related entities.

    Modes:
    - work_related: Fetch works listed in 'related_works' of input works.
    - work_backward: Fetch works listed in 'referenced_works' of input works.
    - work_forward: Fetch works that cite the input works (citing works).
    - work_authors: Fetch authors listed in 'authorships' of input works.
    - work_institutions: Fetch institutions listed in 'authorships' of input works.
    - author_institutions: Fetch institutions listed in 'last_known_institutions' or 'affiliations' of input authors.
    - author_works: Fetch works authored by the input authors.
    """
    try:
        # Resolve input
        effective_input = input_opt or input_path
        if not effective_input:
            typer.echo("Error: Missing input file. Provide via arguments or --input.", err=True)
            raise typer.Exit(1)

        # Validate output
        effective_jsonl_path = validate_output_format_options(
            jsonl_flag, None, output_path
        )

        extracted_ids = set()

        # Reading input file
        try:
            with open(effective_input, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        
                        if mode == ExpandMode.work_forward:
                            # For work_forward, we collect the IDs of the input works themselves
                            work_id = data.get("id")
                            if work_id:
                                clean_id = work_id.replace("https://openalex.org/", "")
                                extracted_ids.add(clean_id)
                        
                        elif mode == ExpandMode.work_backward:
                            # For work_backward, we collect IDs from referenced_works
                            refs = data.get("referenced_works", [])
                            for ref in refs:
                                clean_id = ref.replace("https://openalex.org/", "")
                                extracted_ids.add(clean_id)
                        
                        elif mode == ExpandMode.work_related:
                            # For work_related, we collect IDs from related_works
                            refs = data.get("related_works", [])
                            for ref in refs:
                                clean_id = ref.replace("https://openalex.org/", "")
                                extracted_ids.add(clean_id)
                                
                        elif mode == ExpandMode.work_authors:
                            # For work_authors, we collect IDs from authorships
                            authorships = data.get("authorships", [])
                            for authorship in authorships:
                                author = authorship.get("author", {})
                                author_id = author.get("id")
                                if author_id:
                                    clean_id = author_id.replace("https://openalex.org/", "")
                                    extracted_ids.add(clean_id)

                        elif mode == ExpandMode.work_institutions:
                            # For work_institutions, we collect IDs from institutions in Works' authorships
                            if "authorships" in data:
                                for authorship in data.get("authorships", []):
                                    for inst in authorship.get("institutions", []):
                                        if "id" in inst and inst["id"]:
                                            extracted_ids.add(inst["id"].replace("https://openalex.org/", ""))

                        elif mode == ExpandMode.author_institutions:
                            # For author_institutions, we collect IDs from affiliations/last_known_institutions in Authors
                            if "last_known_institutions" in data:
                                for inst in data.get("last_known_institutions", []):
                                    if "id" in inst and inst["id"]:
                                        extracted_ids.add(inst["id"].replace("https://openalex.org/", ""))
                                for aff in data.get("affiliations", []):
                                    inst = aff.get("institution", {})
                                    if "id" in inst and inst["id"]:
                                        extracted_ids.add(inst["id"].replace("https://openalex.org/", ""))

                        elif mode == ExpandMode.author_works:
                            # For author_works, we collect the IDs of the input authors themselves
                            author_id = data.get("id")
                            if author_id:
                                clean_id = author_id.replace("https://openalex.org/", "")
                                extracted_ids.add(clean_id)

                    except json.JSONDecodeError:
                        continue
        except FileNotFoundError:
            typer.echo(f"Error: Input file '{effective_input}' not found.", err=True)
            raise typer.Exit(1) from None

        if not extracted_ids:
            typer.echo(f"No relevant IDs found in input file for mode '{mode.value}'.", err=True)
            return

        formatted_ids = sorted(list(extracted_ids))
        # typer.echo(f"Found {len(formatted_ids)} unique IDs to process.", err=True)

        # Process based on mode
        if mode == ExpandMode.work_forward:
             # work_forward expansion means finding works that cite these IDs
            query = Works()
            id_string = ",".join(formatted_ids)
            query = add_id_list_option_to_command(query, id_string, "works_cites", Works)

            # Handle potentially large lists or standard query
            results = handle_large_id_list_if_needed(
                query,
                Works,
                True, # all_results
                None, # limit
                effective_jsonl_path,
                normalize=normalize,
            )

            if results is None:
                # Standard query fallback
                results = execute_standard_query(
                    query, "Works", all_results=True, limit=None
                )
                _output_results(
                    results,
                    jsonl_path=effective_jsonl_path,
                    normalize=normalize,
                )

        elif mode == ExpandMode.author_works:
            # author_works expansion means finding works authored by these IDs
            query = Works()
            id_string = ",".join(formatted_ids)
            query = add_id_list_option_to_command(query, id_string, "works_author", Works)

            # Handle potentially large lists or standard query
            results = handle_large_id_list_if_needed(
                query,
                Works,
                True, # all_results
                None, # limit
                effective_jsonl_path,
                normalize=normalize,
            )

            if results is None:
                # Standard query fallback
                results = execute_standard_query(
                    query, "Works", all_results=True, limit=None
                )
                _output_results(
                    results,
                    jsonl_path=effective_jsonl_path,
                    normalize=normalize,
                )

        elif mode == ExpandMode.work_authors:
            # work_authors expansion means fetching these specific Author IDs
            results = asyncio.run(
                _async_retrieve_entities(Authors, formatted_ids, "Authors")
            )
            _output_results(
                results,
                jsonl_path=effective_jsonl_path,
                normalize=normalize,
            )

        elif mode in (ExpandMode.work_institutions, ExpandMode.author_institutions):
            # Fetch these specific Institution IDs
            results = asyncio.run(
                _async_retrieve_entities(Institutions, formatted_ids, "Institutions")
            )
            _output_results(
                results,
                jsonl_path=effective_jsonl_path,
                normalize=normalize,
            )

        else:
            # work_backward and work_related expansion means fetching these specific Work IDs
            results = asyncio.run(
                _async_retrieve_entities(Works, formatted_ids, "Works")
            )
            _output_results(
                results,
                jsonl_path=effective_jsonl_path,
                normalize=normalize,
            )
    except Exception as e:
        _handle_cli_exception(e)


def create_expand_command(app):
    """Create and register the expand command."""
    app.command(name="expand", rich_help_panel="Utility Commands")(expand)
