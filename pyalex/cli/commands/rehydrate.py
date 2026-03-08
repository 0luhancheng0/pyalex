"""Rehydrate dehydrated OpenAlex entity stubs.

Reads a JSONL file of dehydrated entities (e.g. author stubs produced by
``expand --mode work_author``), detects the entity type from the OpenAlex
ID prefix, then fetches full records from the API.

Usage
-----
    pyalex rehydrate authors_stubs.jsonl -o authors_full.jsonl
    pyalex rehydrate -i authors.jsonl --jsonl
"""

import asyncio
import json
from typing import Annotated
from typing import Optional

import typer

from pyalex import Authors
from pyalex import Institutions
from pyalex import Works

from ..utils import _async_retrieve_entities
from ..utils import _handle_cli_exception
from ..utils import _output_results
from .help_panels import OUTPUT_PANEL

# Map OpenAlex ID prefix -> entity class
_PREFIX_TO_CLASS = {
    "W": Works,
    "A": Authors,
    "I": Institutions,
}


def _detect_entity_class(ids: list[str]):
    """Return the entity class inferred from the first recognisable ID prefix.

    OpenAlex short IDs look like ``W123``, ``A456``, ``I789`` after stripping
    the base URL.
    """
    for id_ in ids:
        prefix = id_[0].upper() if id_ else ""
        if prefix in _PREFIX_TO_CLASS:
            return _PREFIX_TO_CLASS[prefix]
    return None


def rehydrate_ids(ids: list[str], entity_class=None) -> list[dict]:
    """Fetch full records for a list of OpenAlex IDs.

    Args:
        ids: List of cleaned OpenAlex IDs (no base-URL prefix).
        entity_class: One of Works, Authors, Institutions.  If None, auto-
            detected from the ID prefix of the first ID.

    Returns:
        List of full entity dicts.

    Raises:
        typer.Exit: If the entity class cannot be detected.
    """
    if entity_class is None:
        entity_class = _detect_entity_class(ids)
    if entity_class is None:
        typer.echo("Error: Could not detect entity type from IDs.", err=True)
        raise typer.Exit(1)

    return asyncio.run(
        _async_retrieve_entities(entity_class, ids, entity_class.__name__)
    )


def create_rehydrate_command(app: typer.Typer) -> None:
    """Register the ``rehydrate`` command on *app*."""
    app.command(
        name="rehydrate",
        help="Fetch full OpenAlex records for dehydrated entity stubs.",
        rich_help_panel="Utility Commands",
    )(rehydrate)


def rehydrate(
    input_path: Annotated[
        Optional[str],
        typer.Argument(
            help="Path to input JSONL file containing dehydrated entity stubs.",
        ),
    ] = None,
    input_opt: Annotated[
        Optional[str],
        typer.Option(
            "--input",
            "-i",
            help="Path to input JSONL file (alternative to positional argument).",
        ),
    ] = None,
    output_path: Annotated[
        Optional[str],
        typer.Option(
            "--output",
            "-o",
            help="Output file path (.jsonl). Defaults to stdout.",
            rich_help_panel=OUTPUT_PANEL,
        ),
    ] = None,
    jsonl_flag: Annotated[
        bool,
        typer.Option(
            "--jsonl",
            help="Write JSON Lines to stdout.",
            rich_help_panel=OUTPUT_PANEL,
        ),
    ] = False,
    normalize: Annotated[
        bool,
        typer.Option(
            "--normalize",
            help="Flatten nested fields with pandas.json_normalize.",
            rich_help_panel=OUTPUT_PANEL,
        ),
    ] = False,
):
    """Fetch full OpenAlex records for dehydrated entity stubs.

    Reads entity IDs from the input JSONL and auto-detects the entity type
    from the OpenAlex ID prefix:

    - ``W…`` → Works
    - ``A…`` → Authors
    - ``I…`` → Institutions

    Example::

        pyalex expand --mode work_author -i works.jsonl -o authors.jsonl
        pyalex rehydrate authors.jsonl -o authors_full.jsonl
        pyalex expand --mode author_institution -i authors_full.jsonl
    """
    effective_input = input_opt or input_path
    if not effective_input:
        typer.echo("Error: Missing input file. Provide as argument or via --input.", err=True)
        raise typer.Exit(1)

    ids: list[str] = []
    with open(effective_input, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            eid = data.get("id", "")
            if eid:
                ids.append(eid.replace("https://openalex.org/", ""))

    if not ids:
        typer.echo("No entity IDs found in input.", err=True)
        return

    entity_class = _detect_entity_class(ids)
    if entity_class is None:
        typer.echo(
            "Error: Could not detect entity type from IDs. "
            "Expected IDs starting with W (Works), A (Authors) or I (Institutions).",
            err=True,
        )
        raise typer.Exit(1)

    typer.echo(
        f"Rehydrating {len(ids)} {entity_class.__name__} records from OpenAlex...",
        err=True,
    )
    results = rehydrate_ids(ids, entity_class=entity_class)
    typer.echo(f"  Fetched {len(results)} full records.", err=True)

    effective_jsonl_path = output_path or (None if not jsonl_flag else None)
    _output_results(results, jsonl_path=effective_jsonl_path, normalize=normalize)
