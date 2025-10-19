"""
Common utilities for PyAlex CLI commands.

This module contains shared utility functions for debugging, data processing,
output formatting, and query execution.
"""

import asyncio
import json
from typing import Any

import typer
from prettytable import PrettyTable

from pyalex import config
from pyalex import invert_abstract
from pyalex.core.config import MAX_PER_PAGE
from pyalex.logger import get_logger

# Initialize logger
logger = get_logger()

# Global state - will be set by main CLI
_debug_mode = False
_dry_run_mode = False
_batch_size = config.cli_batch_size


def _debug_print(message: str, level: str = "INFO"):
    """Print colored debug messages when debug mode is enabled.

    Args:
        message: The message to print.
        level: The log level (ERROR, WARNING, INFO, SUCCESS, STRATEGY, ASYNC, BATCH).
    """
    if not _debug_mode:
        return

    try:
        from rich.console import Console

        console = Console(stderr=True)

        color_map = {
            "ERROR": "red",
            "WARNING": "yellow",
            "INFO": "blue",
            "SUCCESS": "green",
            "STRATEGY": "magenta",
            "ASYNC": "cyan",
            "BATCH": "bright_yellow",
        }

        color = color_map.get(level.upper(), "white")
        console.print(f"[{level}] {message}", style=color)

    except ImportError:
        # Fallback to regular output if rich is not available
        typer.echo(f"[DEBUG {level}] {message}", err=True)


# Progress context tracking to prevent conflicting progress bars
_active_progress_context = None
_batch_progress_context = None
_progress_depth = 0

MAX_WIDTH = config.cli_max_width


def set_global_state(debug_mode: bool, dry_run_mode: bool, batch_size: int) -> None:
    """Set global state from main CLI configuration.

    Args:
        debug_mode: Whether debug mode is enabled.
        dry_run_mode: Whether dry run mode is enabled.
        batch_size: The batch size for processing.
    """
    global _debug_mode, _dry_run_mode, _batch_size
    _debug_mode = debug_mode
    _dry_run_mode = dry_run_mode
    _batch_size = batch_size


def set_batch_progress_context(progress_context: Any | None) -> None:
    """Set the active batch progress context to prevent conflicts.

    Args:
        progress_context: The progress context to set.
    """
    global _batch_progress_context
    _batch_progress_context = progress_context


def get_batch_progress_context() -> Any | None:
    """Get the active batch progress context.

    Returns:
        The active batch progress context, or None if not set.
    """
    return _batch_progress_context


def is_in_batch_context() -> bool:
    """Check if we're currently in a batch processing context.

    Returns:
        True if in batch context, False otherwise.
    """
    return _batch_progress_context is not None


def _enter_progress_context() -> int:
    """Enter a progress context, tracking depth.

    Returns:
        The current progress depth.
    """
    global _progress_depth
    _progress_depth += 1
    return _progress_depth


def _exit_progress_context() -> int:
    """Exit a progress context, tracking depth.

    Returns:
        The current progress depth.
    """
    global _progress_depth
    _progress_depth = max(0, _progress_depth - 1)
    return _progress_depth


def _is_progress_active() -> bool:
    """Check if any progress context is currently active.

    Returns:
        True if progress is active, False otherwise.
    """
    return _progress_depth > 0 or is_in_batch_context()


def _should_show_progress() -> bool:
    """Determine if we should show a new progress display.

    Returns:
        True if progress should be shown, False otherwise.
    """
    return not _is_progress_active()


def _simple_paginate_all(query):
    """Simple pagination to get all results without progress display.

    Args:
        query: The query object to paginate.

    Returns:
        OpenAlexResponseList containing all results.
    """
    paginator = query.paginate(method="cursor", cursor="*", per_page=MAX_PER_PAGE)
    all_results = []
    for batch in paginator:
        if not batch:
            break
        all_results.extend(batch)

    if all_results:
        from pyalex.core.response import OpenAlexResponseList

        return OpenAlexResponseList(all_results, {"count": len(all_results)})
    else:
        from pyalex.core.response import OpenAlexResponseList

        return OpenAlexResponseList([], {"count": 0})


def parse_range_filter(value: str) -> str | None:
    """Parse range or single value for filtering.

    Supports formats:
    - "100" -> exact value 100
    - "100:1000" -> range from 100 to 1000 (returns ">99,<1001" for OpenAlex API)
    - ":1000" -> less than or equal to 1000
    - "100:" -> greater than or equal to 100

    Args:
        value: The range or value to parse.

    Returns:
        Formatted filter value for OpenAlex API, or None if value is empty.

    Raises:
        ValueError: If the value format is invalid or contains non-numeric values.
    """
    if not value:
        return None

    value = value.strip()

    # Check if it's a range (contains colon)
    if ":" in value:
        parts = value.split(":", 1)
        start = parts[0].strip() if parts[0].strip() else None
        end = parts[1].strip() if parts[1].strip() else None

        if start and end:
            # Range: start:end -> use >start-1,<end+1 format for inclusive range
            try:
                start_val = int(start)
                end_val = int(end)
                return f">{start_val - 1},<{end_val + 1}"
            except ValueError as exc:
                raise ValueError(f"Invalid number format in range: {value}") from exc
        elif start:
            # Greater than or equal: start: -> use >start-1 for inclusive
            try:
                start_val = int(start)
                return f">{start_val - 1}"
            except ValueError as exc:
                raise ValueError(f"Invalid number format: {start}") from exc
        elif end:
            # Less than or equal: :end -> use <end+1 for inclusive
            try:
                end_val = int(end)
                return f"<{end_val + 1}"
            except ValueError as exc:
                raise ValueError(f"Invalid number format: {end}") from exc
        else:
            raise ValueError(
                "Invalid range format. Use 'start:end', 'start:', or ':end'"
            )
    else:
        # Single value
        try:
            int(value)  # Validate it's a number
            return value
        except ValueError as exc:
            raise ValueError(f"Invalid number format: {value}") from exc


def apply_range_filter(query, field_name, parsed_value):
    """Apply a parsed range filter to a query object.

    Args:
        query: The query object to apply the filter to.
        field_name: The field name to filter on (e.g., 'works_count', 'summary_stats.h_index').
        parsed_value: The parsed filter value from parse_range_filter.

    Returns:
        The updated query object.
    """
    if not parsed_value:
        return query

    if isinstance(parsed_value, str) and "," in parsed_value:
        # Handle range format like ">99,<501"
        parts = parsed_value.split(",")
        for part in parts:
            part = part.strip()
            if part.startswith(">"):
                min_val = int(part[1:]) + 1  # Convert >99 to >=100
                query = query.filter_gt(**{field_name: min_val - 1})
            elif part.startswith("<"):
                max_val = int(part[1:]) - 1  # Convert <501 to <=500
                query = query.filter_lt(**{field_name: max_val + 1})
    elif isinstance(parsed_value, str) and parsed_value.startswith(">"):
        # Handle ">99" format
        min_val = int(parsed_value[1:]) + 1  # Convert >99 to >=100
        query = query.filter_gt(**{field_name: min_val - 1})
    elif isinstance(parsed_value, str) and parsed_value.startswith("<"):
        # Handle "<501" format
        max_val = int(parsed_value[1:]) - 1  # Convert <501 to <=500
        query = query.filter_lt(**{field_name: max_val + 1})
    else:
        # Handle single value
        query = query.filter(**{field_name: parsed_value})

    return query


def _print_debug_url(query):
    """Print the constructed URL for debugging when verbose mode is enabled.

    Args:
        query: The query object containing the URL to print.
    """
    if _debug_mode:
        from pyalex.logger import log_api_request

        log_api_request(query.url)


def _print_debug_results(results):
    """Print debug information about results when verbose mode is enabled."""
    if _debug_mode and results is not None:
        from pyalex.logger import log_api_response

        log_api_response(results)


def _print_dry_run_query(query_description, url=None, estimated_queries=None):
    """Print dry run information."""
    if _dry_run_mode:
        typer.echo(f"[DRY RUN] {query_description}")
        if url:
            typer.echo(f"  URL: {url}")
        if estimated_queries and estimated_queries > 1:
            typer.echo(f"  Estimated queries: {estimated_queries}")


def _handle_cli_exception(e: Exception) -> None:
    """
    Handle CLI exceptions with specific error types and better messages.

    Args:
        e: Exception to handle
    """
    from pyalex.exceptions import APIError
    from pyalex.exceptions import CLIError
    from pyalex.exceptions import ConfigurationError
    from pyalex.exceptions import DataError
    from pyalex.exceptions import NetworkError
    from pyalex.exceptions import PyAlexException
    from pyalex.exceptions import QueryError
    from pyalex.exceptions import RateLimitError
    from pyalex.exceptions import ValidationError

    if _debug_mode:
        from pyalex.logger import get_logger

        logger = get_logger()
        logger.debug("Full traceback:", exc_info=True)

    # Handle specific exception types with better messages
    if isinstance(e, RateLimitError):
        typer.echo(f"❌ Rate Limit Error: {e.message}", err=True)
        if hasattr(e, "retry_after") and e.retry_after:
            typer.echo(
                f"   Please wait {e.retry_after} seconds before retrying.", err=True
            )
        typer.echo(
            "   Tip: Set OPENALEX_RATE_LIMIT in .env to reduce request rate.", err=True
        )
    elif isinstance(e, NetworkError):
        typer.echo(f"❌ Network Error: {e.message}", err=True)
        if e.url:
            typer.echo(f"   URL: {e.url}", err=True)
        typer.echo("   Please check your internet connection and try again.", err=True)
    elif isinstance(e, APIError):
        typer.echo(f"❌ API Error: {e.message}", err=True)
        if e.status_code:
            typer.echo(f"   Status Code: {e.status_code}", err=True)
        if e.url:
            typer.echo(f"   URL: {e.url}", err=True)
    elif isinstance(e, ValidationError):
        typer.echo(f"❌ Validation Error: {e.message}", err=True)
        if e.field:
            typer.echo(f"   Field: {e.field}", err=True)
        if e.value:
            typer.echo(f"   Invalid value: {e.value}", err=True)
    elif isinstance(e, ConfigurationError):
        typer.echo(f"❌ Configuration Error: {e.message}", err=True)
        if e.config_key:
            typer.echo(f"   Key: {e.config_key}", err=True)
        typer.echo("   Tip: Check your .env file or environment variables.", err=True)
    elif isinstance(e, QueryError):
        typer.echo(f"❌ Query Error: {e.message}", err=True)
        if e.query:
            typer.echo(f"   Query: {e.query}", err=True)
    elif isinstance(e, DataError):
        typer.echo(f"❌ Data Error: {e.message}", err=True)
        if e.data_type:
            typer.echo(f"   Data type: {e.data_type}", err=True)
    elif isinstance(e, CLIError):
        typer.echo(f"❌ CLI Error: {e.message}", err=True)
        if e.command:
            typer.echo(f"   Command: {e.command}", err=True)
    elif isinstance(e, PyAlexException):
        # Generic PyAlex exception
        typer.echo(f"❌ Error: {e.message}", err=True)
        if e.details:
            typer.echo(f"   {e.details}", err=True)
    else:
        # Unknown exception type
        typer.echo(f"❌ Unexpected Error: {str(e)}", err=True)

    # Don't raise typer.Exit here - let the caller handle it


def _clean_ids(id_list, url_prefix="https://openalex.org/"):
    """Clean up a list of IDs by removing URL prefixes."""
    cleaned_ids = []
    for id_str in id_list:
        clean_id = id_str.replace(url_prefix, "").strip()
        clean_id = clean_id.strip("/")
        if clean_id:
            cleaned_ids.append(clean_id)
    return cleaned_ids


async def _async_retrieve_entities(entity_class, ids, class_name):
    """Async function to retrieve entities by IDs using batch requests.

    Exclusively uses async requests (httpx) - no sync fallbacks.
    """
    from pyalex.client.httpx_session import async_batch_requests

    # Calculate number of batches
    num_batches = (len(ids) + _batch_size - 1) // _batch_size

    # Create batches of IDs for concurrent processing
    urls = []
    batch_info = []

    for i in range(0, len(ids), _batch_size):
        batch_ids = ids[i : i + _batch_size]
        batch_info.append(batch_ids)

        if len(batch_ids) == 1:
            # Single ID - use direct retrieval URL
            single_url = (
                f"https://api.openalex.org/"
                f"{entity_class.__name__.lower()}/{batch_ids[0]}"
            )
            urls.append(single_url)
        else:
            # Multiple IDs - use OR operator for batch retrieval
            id_filter = "|".join(batch_ids)
            query = entity_class().filter(openalex_id=id_filter)
            urls.append(query.url)

    # Show progress feedback for multiple batches
    if num_batches > 1 and not _debug_mode:
        # Try to use rich progress
        try:
            from rich.progress import BarColumn
            from rich.progress import Progress
            from rich.progress import SpinnerColumn
            from rich.progress import TextColumn

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TextColumn("({task.completed}/{task.total})"),
            ) as progress:
                task_id = progress.add_task(
                    f"Processing {len(ids):,} {class_name} in {num_batches} concurrent batches",
                    total=100,
                )

                # Execute async requests
                progress.update(
                    task_id, advance=50
                )  # Show progress while making requests
                responses = await async_batch_requests(urls, max_concurrent=5)
                progress.update(task_id, advance=50)  # Complete the progress

        except ImportError:
            # Fallback: simple text message
            typer.echo(
                f"Processing {len(ids):,} {class_name} in {num_batches} concurrent batches...",
                err=True,
            )
            responses = await async_batch_requests(urls, max_concurrent=5)
    else:
        # Single batch or debug mode - no progress display
        responses = await async_batch_requests(urls, max_concurrent=5)

    # Process responses
    all_results = []
    for i, response_data in enumerate(responses):
        batch_ids = batch_info[i]

        if len(batch_ids) == 1:
            # Single entity response
            if "id" in response_data:
                result = entity_class.resource_class(response_data)
                all_results.append(result)
        else:
            # Multiple entities response
            if "results" in response_data:
                for item in response_data["results"]:
                    result = entity_class.resource_class(item)
                    all_results.append(result)

    # Convert abstracts for works if requested
    if class_name == "Works":
        all_results = [_add_abstract_to_work(work) for work in all_results]

    return all_results


def _validate_and_apply_common_options(
    query, all_results, limit, sample, seed, sort_by, select=None
):
    """
    Validate common options and apply sorting, sampling, and field selection to a query.

    Args:
        query: The OpenAlex query object
        all_results: Whether to get all results
        limit: Result limit
        sample: Sample size
        seed: Random seed
        sort_by: Sort specification
        select: Comma-separated list of fields to select

    Returns:
        Modified query object
    """
    # Validate sample and seed options
    if sample is not None:
        if sample < 1 or sample > 10000:
            typer.echo("Error: --sample must be between 1 and 10,000", err=True)
            raise typer.Exit(1)
        if all_results:
            typer.echo("Error: --sample and --all are mutually exclusive", err=True)
            raise typer.Exit(1)

    # Apply sort options
    if sort_by:
        # Parse sort string - can be comma-separated for multiple sorts
        sort_params = {}
        for sort_item in sort_by.split(","):
            sort_item = sort_item.strip()
            if ":" in sort_item:
                field, direction = sort_item.split(":", 1)
                sort_params[field.strip()] = direction.strip()
            else:
                sort_params[sort_item] = "asc"  # Default direction
        query = query.sort(**sort_params)

    # Apply select options
    if select:
        # Parse select string - comma-separated field list
        fields = [field.strip() for field in select.split(",")]
        query = query.select(fields)

    # Apply sample options
    if sample is not None:
        query = query.sample(sample, seed=seed)

    return query


def _execute_query_with_progress(
    query, all_results=False, limit=None, entity_name="results"
):
    """
    Execute a query with progress tracking.
    Enhanced with strategy-based optimization.
    Only shows progress display if no other progress is active.
    """
    # Check if we're already in a progress context before entering a new one
    if _is_progress_active():
        # Already in a progress context, use simple execution without new progress
        if all_results:
            return _simple_paginate_all(query)
        elif limit:
            return query[:limit]
        else:
            return asyncio.run(query.get())

    # Enter progress context and show progress
    _enter_progress_context()
    try:
        # Original progress-enabled logic
        if _debug_mode:
            _debug_print(f"Parameters: all_results={all_results}, limit={limit}")

        # Get count efficiently for strategy determination
        if _debug_mode:
            _debug_print("Getting count with per_page=200 for efficiency")

        first_page_response = query[:200]  # Get first page with more results

        # Convert DataFrame to list of dicts properly
        import pandas as pd

        if isinstance(first_page_response, pd.DataFrame):
            first_page_results = first_page_response.to_dict("records")
        else:
            first_page_results = list(first_page_response)

        count = query.count()

        if _debug_mode:
            _debug_print(f"First page returned: {len(first_page_results)} results")
            _debug_print(f"Total count: {count:,} results")

        # Calculate effective limit
        if all_results:
            effective_limit = count
            strategy_reason = "all results requested"
        elif limit and limit < count:
            effective_limit = limit
            strategy_reason = f"limit ({limit:,}) < count ({count:,})"
        else:
            effective_limit = count
            strategy_reason = (
                f"limit ({limit:,}) >= count ({count:,})"
                if limit
                else "no limit specified"
            )

        if _debug_mode:
            _debug_print(f"Effective limit: {effective_limit:,} ({strategy_reason})")

        # Always show progress indication for CLI operations
        _show_simple_progress(
            f"Fetching {entity_name}", effective_limit, effective_limit
        )

        # Strategy: Single page sufficient
        if effective_limit <= len(first_page_results):
            if _debug_mode:
                _debug_print(
                    "Strategy: Single page sufficient (already fetched)", "STRATEGY"
                )
            return first_page_results[:effective_limit]

        # Always use async pagination - no sync fallbacks
        if _debug_mode:
            _debug_print(
                f"Strategy: Async pagination ({effective_limit:,} results)", "STRATEGY"
            )
        return _execute_async_with_progress(
            query, effective_limit, entity_name, first_page_results
        )

    finally:
        _exit_progress_context()


def _show_simple_progress(description, current, total):
    """Show a simple progress indication for quick operations."""
    # Always show progress for CLI operations when not in batch context
    if is_in_batch_context():
        if _debug_mode:
            logger.debug(f"{description} (in batch context)")
        return

    try:
        from rich.progress import Progress
        from rich.progress import SpinnerColumn
        from rich.progress import TextColumn

        with Progress(
            SpinnerColumn(), TextColumn(f"[bold blue]{description}...")
        ) as progress:
            progress.add_task("", total=total)
            # Brief pause to show the progress
            import time

            time.sleep(0.1)
    except ImportError:
        typer.echo(f"{description}...", err=True)


def _create_response_from_results(results, meta, response_class):
    """Create a response object from results list."""
    try:
        # Try to use the same class as the original response
        return response_class(results, meta)
    except Exception:
        # Fallback to basic list
        return results


def _execute_async_with_progress(
    query, effective_limit, entity_name, first_page_results
):
    """Execute async pagination with progress bar.

    Handles both sync and async contexts gracefully by using the safe runner.
    """
    import traceback

    # Import the safe async runner from base module
    from pyalex.entities.base import _run_async_safely

    try:
        # Use the safe async runner which handles both sync and async contexts
        if _debug_mode:
            _debug_print("Using safe async execution", "ASYNC")
        return _run_async_safely(
            _async_paginate_optimized(
                query, effective_limit, entity_name, first_page_results
            )
        )
    except Exception as e:
        # Print full traceback and exit - do not fall back to sync
        _debug_print("ASYNC EXECUTION FAILED - This is a critical error:", "ERROR")
        _debug_print(f"Error: {e}", "ERROR")
        _debug_print("Full traceback:", "ERROR")
        _debug_print(traceback.format_exc(), "ERROR")
        raise RuntimeError(f"Async execution failed: {e}") from e


async def _async_paginate_optimized(
    query, effective_limit, entity_name, first_page_results
):
    """Optimized async pagination that reuses first page results."""
    # If we're in a batch context, don't create competing progress displays
    if is_in_batch_context():
        # Just return the results without creating a new progress context
        first_page_count = len(first_page_results)
        remaining_needed = max(0, effective_limit - first_page_count)

        if _debug_mode:
            _debug_print(
                f"Async paginate in batch context: {effective_limit:,} total, "
                f"{remaining_needed:,} remaining",
                "BATCH",
            )

        if remaining_needed == 0:
            return first_page_results[:effective_limit]

        # Get remaining results without progress display
        remaining_results = await query.get(limit=remaining_needed)
        all_results = first_page_results + list(remaining_results)
        return all_results[:effective_limit]

    # Normal progress display for non-batch context
    if _debug_mode:
        _debug_print(
            f"Starting async pagination for {effective_limit:,} results", "ASYNC"
        )

    # Calculate remaining results needed
    first_page_count = len(first_page_results)
    remaining_needed = max(0, effective_limit - first_page_count)

    if remaining_needed == 0:
        # We already have everything we need
        if _debug_mode:
            _debug_print("First page contains all needed results", "SUCCESS")
        return _create_response_from_results(
            first_page_results[:effective_limit], {"count": effective_limit}, list
        )

    # Use the async method which has its own built-in progress tracking
    # This avoids duplicate progress bars
    try:
        # Use the built-in async pagination which has proper progress tracking
        remaining_results = await query._get_async_basic_paging(
            total_count=remaining_needed, limit=remaining_needed
        )

        all_results = first_page_results + list(remaining_results)
        return all_results[:effective_limit]

    except AttributeError:
        # Fallback if _get_async_basic_paging is not available
        logger.info(f"Fetching remaining {remaining_needed:,} {entity_name}...")
        remaining_results = await query.get(limit=remaining_needed)

        # Convert DataFrame to list of dicts if needed
        import pandas as pd

        if isinstance(remaining_results, pd.DataFrame):
            remaining_results = remaining_results.to_dict("records")

        all_results = first_page_results + list(remaining_results)
        return all_results[:effective_limit]


def _is_progress_active():
    """Check if we're already in a progress context to avoid nested displays."""
    import threading

    return getattr(threading.current_thread(), "_pyalex_batch_context", False)


def _paginate_with_progress(query, entity_type_name="results"):
    """
    Paginate through all results with a progress bar.
    Avoids nested progress displays by directly handling pagination.
    """
    if _is_progress_active():
        # Already in a progress context, just paginate without new progress
        paginator = query.paginate(method="cursor", cursor="*", per_page=MAX_PER_PAGE)
        all_results = []
        for batch in paginator:
            if not batch:
                break
            all_results.extend(batch)

        if all_results:
            from pyalex.core.response import OpenAlexResponseList

            return OpenAlexResponseList(all_results, {"count": len(all_results)})
        else:
            from pyalex.core.response import OpenAlexResponseList

            return OpenAlexResponseList([], {"count": 0})

    # Not in a progress context, safe to create one
    return _execute_query_with_progress(
        query, all_results=True, entity_name=entity_type_name
    )


def _execute_query_smart(query, all_results=False, limit=None):
    """Execute query using the unified progress system.

    Exclusively uses async requests - no sync fallbacks.
    """
    return _execute_query_with_progress(query, all_results, limit, "results")


def _add_abstract_to_work(work_dict):
    """Convert inverted abstract index to readable abstract for a work."""
    if (
        isinstance(work_dict, dict)
        and "abstract_inverted_index" in work_dict
        and work_dict["abstract_inverted_index"] is not None
    ):
        work_dict["abstract"] = invert_abstract(work_dict["abstract_inverted_index"])
    return work_dict


def _output_results(
    results,
    json_path: str | None = None,
    parquet_path: str | None = None,
    single: bool = False,
    grouped: bool = False,
):
    """Output results in table, JSON, or Parquet format."""
    # Debug: print type of results
    import sys

    if hasattr(sys, "_debug_output"):
        print(
            f"DEBUG _output_results: type={type(results)}, "
            f"hasattr to_dict={hasattr(results, 'to_dict')}",
            file=sys.stderr,
        )
        if hasattr(results, "__iter__") and not isinstance(
            results, str | dict
        ):
            try:
                print(f"DEBUG _output_results: len={len(results)}", file=sys.stderr)
            except Exception:
                pass

    # Handle None or empty results
    if results is None:
        if json_path:
            data = []
            if json_path == "-":
                # Output JSON to stdout
                typer.echo(json.dumps(data, indent=2))
            else:
                # Save JSON to file
                with open(json_path, "w") as f:
                    json.dump(data, f, indent=2)
        elif parquet_path:
            # Create empty DataFrame and save to parquet
            import pandas as pd
            df = pd.DataFrame()
            df.to_parquet(parquet_path, index=False)
            typer.echo(f"Empty results saved to {parquet_path}")
        else:
            typer.echo("No results found.")
        return

    # Convert DataFrame to list of dicts if needed
    try:
        import pandas as pd

        if isinstance(results, pd.DataFrame):
            results_df = results
            results = results.to_dict("records")
        elif hasattr(results, "to_dict") and callable(results.to_dict):
            # It's a DataFrame or DataFrame-like object
            results_df = results
            results = results.to_dict("records")
        elif not isinstance(results, list):
            # Single item, wrap in list
            results = [results]
            results_df = None
        else:
            results_df = None
    except ImportError:
        # pandas not installed, handle without DataFrame check
        if hasattr(results, "to_dict") and callable(results.to_dict):
            results = results.to_dict("records")
        elif not isinstance(results, list):
            results = [results]
        results_df = None

    if not single and not grouped and (not results or len(results) == 0):
        if json_path:
            data = []
            if json_path == "-":
                # Output JSON to stdout
                typer.echo(json.dumps(data, indent=2))
            else:
                # Save JSON to file
                with open(json_path, "w") as f:
                    json.dump(data, f, indent=2)
        elif parquet_path:
            # Create empty DataFrame and save to parquet
            import pandas as pd
            df = pd.DataFrame()
            df.to_parquet(parquet_path, index=False)
            typer.echo(f"Empty results saved to {parquet_path}")
        else:
            typer.echo("No results found.")
        return

    if parquet_path:
        # Save to Parquet file with normalization
        import pandas as pd
        
        # Convert to DataFrame if needed
        if results_df is not None:
            df = results_df
        else:
            if single:
                df = pd.DataFrame([dict(results)])
            elif grouped:
                df = pd.DataFrame([dict(r) for r in results])
            else:
                df = pd.DataFrame([dict(r) for r in results])
        
        # Normalize the DataFrame to flatten nested structures
        # This exposes all attributes for downstream processing
        df = pd.json_normalize(df.to_dict(orient="records"))
        
        # Save to parquet
        df.to_parquet(parquet_path, index=False)
        typer.echo(f"Results saved to {parquet_path}")
        
    elif json_path:
        # Prepare JSON data
        if single:
            data = dict(results)
        elif grouped:
            # For grouped data, preserve the original structure
            data = [dict(r) for r in results]
        else:
            data = [dict(r) for r in results]

        if json_path == "-":
            # Output JSON to stdout
            typer.echo(json.dumps(data, indent=2))
        else:
            # Save JSON to file
            with open(json_path, "w") as f:
                json.dump(data, f, indent=2)

    else:
        # Display table format to stdout
        _output_table(results, single, grouped)


def _output_table(results, single: bool = False, grouped: bool = False):
    """Output results in table format using PrettyTable.

    Uses the TableFormatterFactory to automatically detect entity type
    and format results appropriately.
    """
    from pyalex.cli.formatters import TableFormatterFactory

    # Handle None results
    if results is None:
        typer.echo("No results found.")
        return

    # Check that results are valid
    if results and len(results) > 0:
        first_item = results[0]
        if not isinstance(first_item, dict):
            raise ValueError(
                f"Expected list of dicts, got list of {type(first_item).__name__}"
            )

    # For single items, wrap in a list for consistent processing
    if single:
        results = [results]

    # Handle empty results
    if len(results) == 0:
        typer.echo("No results found.")
        return

    # Use factory to create and populate table
    table = TableFormatterFactory.format_results(
        results, grouped=grouped, max_width=MAX_WIDTH
    )

    typer.echo(table)


def _output_grouped_results(
    results, json_path: str | None = None, parquet_path: str | None = None
):
    """Output grouped results in table, JSON, or Parquet format."""
    import pandas as pd

    if results is None:
        if json_path:
            data = []
            if json_path == "-":
                # Output JSON to stdout
                typer.echo(json.dumps(data, indent=2))
            else:
                # Save JSON to file
                with open(json_path, "w") as f:
                    json.dump(data, f, indent=2)
        elif parquet_path:
            # Create empty DataFrame and save to parquet
            df = pd.DataFrame()
            df.to_parquet(parquet_path, index=False)
            typer.echo(f"Empty grouped results saved to {parquet_path}")
        else:
            typer.echo("No grouped results found.")
        return

    # When group-by is used, the results list itself contains the grouped data
    grouped_data = results

    # Convert DataFrame to list of dicts if needed
    if isinstance(grouped_data, pd.DataFrame):
        grouped_df = grouped_data
        grouped_data = grouped_data.to_dict("records")
    else:
        grouped_df = None

    # Check for empty results
    is_empty = False
    if hasattr(grouped_data, "__len__"):
        is_empty = len(grouped_data) == 0
    else:
        is_empty = not bool(grouped_data)

    if is_empty:
        if json_path:
            data = []
            if json_path == "-":
                # Output JSON to stdout
                typer.echo(json.dumps(data, indent=2))
            else:
                # Save JSON to file
                with open(json_path, "w") as f:
                    json.dump(data, f, indent=2)
        elif parquet_path:
            # Create empty DataFrame and save to parquet
            df = pd.DataFrame()
            df.to_parquet(parquet_path, index=False)
            typer.echo(f"Empty grouped results saved to {parquet_path}")
        else:
            typer.echo("No grouped results found.")
        return

    if parquet_path:
        # Save to Parquet file with normalization
        if grouped_df is not None:
            df = grouped_df
        else:
            df = pd.DataFrame([dict(item) for item in grouped_data])
        
        # Normalize the DataFrame to flatten nested structures
        # This exposes all attributes for downstream processing
        df = pd.json_normalize(df.to_dict(orient="records"))
        
        df.to_parquet(parquet_path, index=False)
        typer.echo(f"Grouped results saved to {parquet_path}")
        
    elif json_path:
        # Prepare JSON data
        data = [dict(item) for item in grouped_data]

        if json_path == "-":
            # Output JSON to stdout
            typer.echo(json.dumps(data, indent=2))
        else:
            # Save JSON to file
            with open(json_path, "w") as f:
                json.dump(data, f, indent=2)
            typer.echo(f"Grouped results saved to {json_path}")
    else:
        # Display table format to stdout
        table = PrettyTable()
        table.field_names = ["Key", "Display Name", "Count"]
        table.max_width = MAX_WIDTH
        table.align = "l"

        for group in grouped_data:
            key = group.get("key", "Unknown")
            display_name = group.get("key_display_name", key)
            count = group.get("count", 0)

            table.add_row([key, display_name, f"{count:,}"])

        typer.echo(table)
