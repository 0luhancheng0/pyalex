"""
Expand command for PyAlex CLI.

Unified command to expand works by fetching related, referenced, or citing works.
"""

import asyncio
import json
import random
from collections import Counter
from enum import Enum
from typing import Annotated
from typing import Optional

import typer

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
from .rehydrate import rehydrate_ids


def _sample_ids(id_counts: Counter, limit: int | None, seed: int = 42) -> list[str]:
    """Return up to *limit* IDs, prioritising those with the highest frequency.

    IDs that appear in more input items (higher count) are preferred. Within
    equal-frequency buckets the selection is deterministically random.

    Args:
        id_counts: Counter mapping entity ID -> number of input items it appeared in.
        limit: Maximum number of IDs to return. ``None`` means no limit.
        seed: Random seed for tie-breaking reproducibility.

    Returns:
        List of IDs sorted descending by frequency, capped at *limit*.
    """
    if not id_counts:
        return []
    # Sort by frequency desc, then by ID asc for determinism
    sorted_ids = sorted(id_counts.keys(), key=lambda k: (-id_counts[k], k))
    if limit is None or len(sorted_ids) <= limit:
        return sorted_ids
    # Beyond top-N by frequency we do random tie-breaking within the boundary bucket
    cutoff_freq = id_counts[sorted_ids[limit - 1]]
    definite = [i for i in sorted_ids if id_counts[i] > cutoff_freq]
    borderline = [i for i in sorted_ids if id_counts[i] == cutoff_freq]
    rng = random.Random(seed)
    rng.shuffle(borderline)
    return (definite + borderline)[: limit]


class ExpandMode(str, Enum):
    work_related = "work_related"
    work_forward = "work_forward"
    work_backward = "work_backward"
    work_author = "work_author"
    work_institution = "work_institution"
    author_institution = "author_institution"
    author_work = "author_work"
    topic_work = "topic_work"


class AuthorPosition(str, Enum):
    """Filter for authorship position in work_author mode."""
    all = "all"                   # no filter (default)
    first = "first"               # author_position == "first"
    last = "last"                 # author_position == "last"
    corresponding = "corresponding"  # is_corresponding == True


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
            help=(
                "Expansion mode: "
                "'work_related' (related_works), "
                "'work_backward' (referenced_works), "
                "'work_forward' (citing works), "
                "'work_author' (authors of the input works), "
                "'work_institution' (institutions of the input works), "
                "'author_institution' (institutions of the input authors), "
                "'author_work' (works of the input authors), "
                "'topic_work' (works belonging to the input topics)."
            ),
        ),
    ] = ExpandMode.work_related,
    limit: Annotated[
        Optional[int],
        typer.Option(
            "--limit",
            "-l",
            help=(
                "Maximum number of entities to output. By default all entities are "
                "returned. For ID-collection modes (work_backward, work_related, "
                "work_author, work_institution, author_institution) the "
                "most-frequently-occurring IDs are kept first when a limit is set. "
                "For query modes (author_work, work_forward) the API is queried "
                "with this limit, sorted by citation count descending."
            ),
            rich_help_panel=OUTPUT_PANEL,
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
    normalize: Annotated[
        bool,
        typer.Option(
            "--normalize",
            help="Flatten nested fields using pandas.json_normalize before emitting results",
            rich_help_panel=OUTPUT_PANEL,
        ),
    ] = False,
    author_position: Annotated[
        AuthorPosition,
        typer.Option(
            "--author-position",
            "-p",
            help=(
                "Only applies to --mode work_author. "
                "'all' (default): every author. "
                "'first': only first authors (author_position='first'). "
                "'last': only last authors (author_position='last'). "
                "'corresponding': only corresponding authors (is_corresponding=True)."
            ),
        ),
    ] = AuthorPosition.all,
):
    """
    Expand a set of entities by fetching related entities.

    Modes:
    - work_related: Fetch works listed in 'related_works' of input works.
    - work_backward: Fetch works listed in 'referenced_works' of input works.
    - work_forward: Fetch works that cite the input works (citing works).
    - work_author: Fetch author listed in 'authorships' of input works.
    - work_institution: Fetch institution listed in 'authorships' of input works.
    - author_institution: Fetch institution listed in 'last_known_institutions' or 'affiliations' of input authors.
    - author_work: Fetch work authored by the input authors.
    - topic_work: Fetch work belonging to the input topics.

    By default all entities are returned. Pass --limit N to cap the output.
    """
    if author_position != AuthorPosition.all and mode != ExpandMode.work_author:
        typer.echo(
            "Warning: --author-position is only used in work_author mode; ignored.",
            err=True,
        )
    effective_limit: int | None = limit

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

        # Use Counter so we know how many input items each ID appeared in.
        # inline_records caches entity data extracted directly from the input
        # for modes that don't need a secondary API call (work_author, work_institution).
        id_counts: Counter = Counter()
        inline_records: dict[str, dict] = {}
        # Author IDs collected from dehydrated records (for auto-rehydrate fallback)
        dehydrated_author_ids: list[str] = []

        with open(effective_input, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)

                    if mode == ExpandMode.work_forward:
                        work_id = data.get("id")
                        if work_id:
                            clean_id = work_id.replace("https://openalex.org/", "")
                            id_counts[clean_id] += 1

                    elif mode == ExpandMode.work_backward:
                        refs = data.get("referenced_works", [])
                        for ref in refs:
                            id_counts[ref.replace("https://openalex.org/", "")] += 1

                    elif mode == ExpandMode.work_related:
                        refs = data.get("related_works", [])
                        for ref in refs:
                            id_counts[ref.replace("https://openalex.org/", "")] += 1

                    elif mode == ExpandMode.work_author:
                        # Cache the author stub from authorships so we can emit
                        # records directly without a secondary API call.
                        for authorship in data.get("authorships", []):
                            # Apply position filter
                            if author_position == AuthorPosition.first:
                                if authorship.get("author_position") != "first":
                                    continue
                            elif author_position == AuthorPosition.last:
                                if authorship.get("author_position") != "last":
                                    continue
                            elif author_position == AuthorPosition.corresponding:
                                if not authorship.get("is_corresponding", False):
                                    continue

                            author = authorship.get("author", {})
                            author_id = author.get("id")
                            if author_id:
                                clean_id = author_id.replace("https://openalex.org/", "")
                                id_counts[clean_id] += 1
                                if clean_id not in inline_records:
                                    inline_records[clean_id] = {
                                        "id": author_id,
                                        "display_name": author.get("display_name"),
                                        "orcid": author.get("orcid"),
                                    }

                    elif mode == ExpandMode.work_institution:
                        # Cache institution stubs from authorships directly.
                        for authorship in data.get("authorships", []):
                            for inst in authorship.get("institutions", []):
                                inst_id = inst.get("id")
                                if inst_id:
                                    clean_id = inst_id.replace("https://openalex.org/", "")
                                    id_counts[clean_id] += 1
                                    if clean_id not in inline_records:
                                        inline_records[clean_id] = {
                                            "id": inst_id,
                                            "display_name": inst.get("display_name"),
                                            "ror": inst.get("ror"),
                                            "country_code": inst.get("country_code"),
                                            "type": inst.get("type"),
                                        }

                    elif mode == ExpandMode.author_institution:
                        # Track the author's own ID so we can rehydrate if needed
                        author_id = data.get("id")
                        if author_id:
                            dehydrated_author_ids.append(
                                author_id.replace("https://openalex.org/", "")
                            )
                        for inst in data.get("last_known_institutions", []):
                            if inst.get("id"):
                                id_counts[inst["id"].replace("https://openalex.org/", "")] += 1
                        for aff in data.get("affiliations", []):
                            inst = aff.get("institution", {})
                            if inst.get("id"):
                                id_counts[inst["id"].replace("https://openalex.org/", "")] += 1

                    elif mode == ExpandMode.author_work:
                        author_id = data.get("id")
                        if author_id:
                            id_counts[author_id.replace("https://openalex.org/", "")] += 1

                    elif mode == ExpandMode.topic_work:
                        topic_id = data.get("id")
                        if topic_id:
                            id_counts[topic_id.replace("https://openalex.org/", "")] += 1

                except json.JSONDecodeError:
                    continue

        if not id_counts:
            # Special case: author_institution with dehydrated input → auto-rehydrate
            if mode == ExpandMode.author_institution and dehydrated_author_ids:
                typer.echo(
                    "  Input author records appear dehydrated (no affiliations found). "
                    "Auto-rehydrating from OpenAlex...",
                    err=True,
                )
                from pyalex import Authors
                full_authors = rehydrate_ids(dehydrated_author_ids, entity_class=Authors)
                typer.echo(f"  Fetched {len(full_authors)} full author records.", err=True)
                for author in full_authors:
                    for inst in author.get("last_known_institutions", []):
                        if inst.get("id"):
                            id_counts[inst["id"].replace("https://openalex.org/", "")] += 1
                    for aff in author.get("affiliations", []):
                        inst = aff.get("institution", {})
                        if inst.get("id"):
                            id_counts[inst["id"].replace("https://openalex.org/", "")] += 1

            if not id_counts:
                typer.echo(
                    f"No relevant IDs found in input file for mode '{mode.value}'.",
                    err=True,
                )
                return

        total_found = len(id_counts)
        # For ID-collection modes, cap using frequency-weighted sampling.
        # Query modes (author_work, work_forward) handle the limit at API level below.
        id_collection_modes = {
            ExpandMode.work_backward,
            ExpandMode.work_related,
            ExpandMode.work_author,
            ExpandMode.work_institution,
            ExpandMode.author_institution,
        }
        if mode in id_collection_modes:
            formatted_ids = _sample_ids(id_counts, effective_limit)
            if effective_limit is not None and total_found > effective_limit:
                typer.echo(
                    f"  Sampled {len(formatted_ids)} / {total_found} extracted IDs "
                    f"(--limit {effective_limit}; highest-frequency first).",
                    err=True,
                )
        else:
            # For query modes use all IDs — API limit applied below
            formatted_ids = _sample_ids(id_counts, None)

        # Process based on mode
        if mode == ExpandMode.work_forward:
            query = Works()
            id_string = ",".join(formatted_ids)
            query = add_id_list_option_to_command(query, id_string, "works_cites", Works)
            if effective_limit is not None:
                query = query.sort(cited_by_count="desc")

            results = handle_large_id_list_if_needed(
                query,
                Works,
                effective_limit is None,  # all_results
                effective_limit,
                effective_jsonl_path,
                normalize=normalize,
            )

            if results is None:
                results = execute_standard_query(
                    query, "Works",
                    all_results=effective_limit is None,
                    limit=effective_limit,
                )
                _output_results(results, jsonl_path=effective_jsonl_path, normalize=normalize)

        elif mode == ExpandMode.author_work:
            query = Works()
            id_string = ",".join(formatted_ids)
            query = add_id_list_option_to_command(query, id_string, "works_author", Works)
            if effective_limit is not None:
                query = query.sort(cited_by_count="desc")

            results = handle_large_id_list_if_needed(
                query,
                Works,
                effective_limit is None,  # all_results
                effective_limit,
                effective_jsonl_path,
                normalize=normalize,
            )

            if results is None:
                results = execute_standard_query(
                    query, "Works",
                    all_results=effective_limit is None,
                    limit=effective_limit,
                )
                _output_results(results, jsonl_path=effective_jsonl_path, normalize=normalize)

        elif mode == ExpandMode.work_author:
            # Emit author stubs extracted directly from the input works.
            # No secondary API call needed — strictly enforces --limit.
            results = [inline_records[aid] for aid in formatted_ids if aid in inline_records]
            _output_results(results, jsonl_path=effective_jsonl_path, normalize=normalize)

        elif mode == ExpandMode.topic_work:
            query = Works()
            id_string = ",".join(formatted_ids)
            query = add_id_list_option_to_command(query, id_string, "works_topic", Works)
            if effective_limit is not None:
                query = query.sort(cited_by_count="desc")

            results = handle_large_id_list_if_needed(
                query,
                Works,
                effective_limit is None,  # all_results
                effective_limit,
                effective_jsonl_path,
                normalize=normalize,
            )

            if results is None:
                results = execute_standard_query(
                    query, "Works",
                    all_results=effective_limit is None,
                    limit=effective_limit,
                )
                _output_results(results, jsonl_path=effective_jsonl_path, normalize=normalize)


        elif mode == ExpandMode.work_institution:
            # Emit institution stubs extracted directly from the input works.
            results = [inline_records[iid] for iid in formatted_ids if iid in inline_records]
            _output_results(results, jsonl_path=effective_jsonl_path, normalize=normalize)

        elif mode == ExpandMode.author_institution:
            # Fetch institution full records from the API (not cached inline).
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
