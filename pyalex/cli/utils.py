"""
Common utilities for PyAlex CLI commands.

This module contains shared utility functions for debugging, data processing,
output formatting, and query execution.
"""

import asyncio
import json
from typing import Optional

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
            "BATCH": "bright_yellow"
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


def set_batch_progress_context(progress_context: Optional[any]) -> None:
    """Set the active batch progress context to prevent conflicts.
    
    Args:
        progress_context: The progress context to set.
    """
    global _batch_progress_context
    _batch_progress_context = progress_context


def get_batch_progress_context() -> Optional[any]:
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


def parse_range_filter(value: str) -> Optional[str]:
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
    if ':' in value:
        parts = value.split(':', 1)
        start = parts[0].strip() if parts[0].strip() else None
        end = parts[1].strip() if parts[1].strip() else None
        
        if start and end:
            # Range: start:end -> use >start-1,<end+1 format for inclusive range
            try:
                start_val = int(start)
                end_val = int(end)
                return f">{start_val-1},<{end_val+1}"
            except ValueError as exc:
                raise ValueError(f"Invalid number format in range: {value}") from exc
        elif start:
            # Greater than or equal: start: -> use >start-1 for inclusive
            try:
                start_val = int(start)
                return f">{start_val-1}"
            except ValueError as exc:
                raise ValueError(f"Invalid number format: {start}") from exc
        elif end:
            # Less than or equal: :end -> use <end+1 for inclusive
            try:
                end_val = int(end)
                return f"<{end_val+1}"
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
        
    if isinstance(parsed_value, str) and ',' in parsed_value:
        # Handle range format like ">99,<501"
        parts = parsed_value.split(',')
        for part in parts:
            part = part.strip()
            if part.startswith('>'):
                min_val = int(part[1:]) + 1  # Convert >99 to >=100
                query = query.filter_gt(**{field_name: min_val - 1})
            elif part.startswith('<'):
                max_val = int(part[1:]) - 1  # Convert <501 to <=500
                query = query.filter_lt(**{field_name: max_val + 1})
    elif isinstance(parsed_value, str) and parsed_value.startswith('>'):
        # Handle ">99" format
        min_val = int(parsed_value[1:]) + 1  # Convert >99 to >=100
        query = query.filter_gt(**{field_name: min_val - 1})
    elif isinstance(parsed_value, str) and parsed_value.startswith('<'):
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
    from pyalex.exceptions import (
        PyAlexException, NetworkError, APIError, RateLimitError,
        ValidationError, ConfigurationError, QueryError, DataError, CLIError
    )
    
    if _debug_mode:
        from pyalex.logger import get_logger
        logger = get_logger()
        logger.debug("Full traceback:", exc_info=True)
    
    # Handle specific exception types with better messages
    if isinstance(e, RateLimitError):
        typer.echo(f"❌ Rate Limit Error: {e.message}", err=True)
        if hasattr(e, 'retry_after') and e.retry_after:
            typer.echo(f"   Please wait {e.retry_after} seconds before retrying.", err=True)
        typer.echo("   Tip: Set OPENALEX_RATE_LIMIT in .env to reduce request rate.", err=True)
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


def _clean_ids(id_list, url_prefix='https://openalex.org/'):
    """Clean up a list of IDs by removing URL prefixes."""
    cleaned_ids = []
    for id_str in id_list:
        clean_id = id_str.replace(url_prefix, '').strip()
        clean_id = clean_id.strip('/')
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
        batch_ids = ids[i:i + _batch_size]
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
                TextColumn("({task.completed}/{task.total})")
            ) as progress:
                task_id = progress.add_task(
                    f"Processing {len(ids):,} {class_name} in {num_batches} concurrent batches", 
                    total=100
                )
                
                # Execute async requests
                progress.update(task_id, advance=50)  # Show progress while making requests
                responses = await async_batch_requests(urls, max_concurrent=5)
                progress.update(task_id, advance=50)  # Complete the progress
                
        except ImportError:
            # Fallback: simple text message
            typer.echo(f"Processing {len(ids):,} {class_name} in {num_batches} concurrent batches...", err=True)
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
            if 'id' in response_data:
                result = entity_class.resource_class(response_data)
                all_results.append(result)
        else:
            # Multiple entities response
            if 'results' in response_data:
                for item in response_data['results']:
                    result = entity_class.resource_class(item)
                    all_results.append(result)
    
    # Convert abstracts for works if requested
    if class_name == 'Works':
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
        for sort_item in sort_by.split(','):
            sort_item = sort_item.strip()
            if ':' in sort_item:
                field, direction = sort_item.split(':', 1)
                sort_params[field.strip()] = direction.strip()
            else:
                sort_params[sort_item] = "asc"  # Default direction
        query = query.sort(**sort_params)
    
    # Apply select options
    if select:
        # Parse select string - comma-separated field list
        fields = [field.strip() for field in select.split(',')]
        query = query.select(fields)
    
    # Apply sample options
    if sample is not None:
        query = query.sample(sample, seed=seed)
    
    return query


def _execute_query_with_progress(query, all_results=False, limit=None, entity_name="results"):
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
                f"limit ({limit:,}) >= count ({count:,})" if limit 
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
                _debug_print("Strategy: Single page sufficient (already fetched)", "STRATEGY")
            return first_page_results[:effective_limit]
        
        # Always use async pagination - no sync fallbacks
        if _debug_mode:
            _debug_print(f"Strategy: Async pagination ({effective_limit:,} results)", "STRATEGY")
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
            SpinnerColumn(), 
            TextColumn(f"[bold blue]{description}...")
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


def _execute_async_with_progress(query, effective_limit, entity_name, first_page_results):
    """Execute async pagination with progress bar."""
    import traceback
    
    try:
        # Check if we're already in an event loop
        try:
            asyncio.get_running_loop()
            # We're in an async context - this is the problematic case
            error_msg = (
                "Cannot execute async pagination: already in event loop. "
                "This indicates a nested async call which is not supported. "
                "Please run this command outside of an async context."
            )
            _debug_print(error_msg, "ERROR")
            raise RuntimeError(error_msg)
        except RuntimeError as loop_error:
            if "no running event loop" in str(loop_error).lower():
                # No event loop running, safe to use asyncio.run
                if _debug_mode:
                    _debug_print("No event loop running, using asyncio.run", "ASYNC")
                return asyncio.run(_async_paginate_optimized(
                    query, effective_limit, entity_name, first_page_results
                ))
            else:
                # Re-raise the original RuntimeError
                raise
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
                "BATCH"
            )
        
        if remaining_needed == 0:
            return first_page_results[:effective_limit]
        
        # Get remaining results without progress display
        remaining_results = await query.get(limit=remaining_needed)
        all_results = first_page_results + list(remaining_results)
        return all_results[:effective_limit]

    # Normal progress display for non-batch context
    if _debug_mode:
        _debug_print(f"Starting async pagination for {effective_limit:,} results", "ASYNC")
    
    # Calculate remaining results needed
    first_page_count = len(first_page_results)
    remaining_needed = max(0, effective_limit - first_page_count)
    
    if remaining_needed == 0:
        # We already have everything we need
        if _debug_mode:
            _debug_print("First page contains all needed results", "SUCCESS")
        return _create_response_from_results(
            first_page_results[:effective_limit], 
            {"count": effective_limit}, 
            list
        )

    # Use the async method which has its own built-in progress tracking
    # This avoids duplicate progress bars
    try:
        # Use the built-in async pagination which has proper progress tracking
        remaining_results = await query._get_async_basic_paging(
            total_count=remaining_needed,
            limit=remaining_needed
        )
        
        all_results = first_page_results + list(remaining_results)
        return all_results[:effective_limit]
        
    except AttributeError:
        # Fallback if _get_async_basic_paging is not available
        logger.info(f"Fetching remaining {remaining_needed:,} {entity_name}...")
        remaining_results = await query.get(limit=remaining_needed)
        all_results = first_page_results + list(remaining_results)
        return all_results[:effective_limit]


def _is_progress_active():
    """Check if we're already in a progress context to avoid nested displays."""
    import threading
    return getattr(threading.current_thread(), '_pyalex_batch_context', False)


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
    if (isinstance(work_dict, dict) and 
        'abstract_inverted_index' in work_dict and 
        work_dict['abstract_inverted_index'] is not None):
        work_dict['abstract'] = invert_abstract(work_dict['abstract_inverted_index'])
    return work_dict


def _output_results(
    results, 
    json_path: Optional[str] = None, 
    single: bool = False, 
    grouped: bool = False
):
    """Output results in table format to stdout or JSON format to file/stdout."""
    # Handle None or empty results
    if results is None:
        if json_path:
            data = []
            if json_path == "-":
                # Output JSON to stdout
                typer.echo(json.dumps(data, indent=2))
            else:
                # Save JSON to file
                with open(json_path, 'w') as f:
                    json.dump(data, f, indent=2)
        else:
            typer.echo("No results found.")
        return
    
    if not single and not grouped and (not results or len(results) == 0):
        if json_path:
            data = []
            if json_path == "-":
                # Output JSON to stdout
                typer.echo(json.dumps(data, indent=2))
            else:
                # Save JSON to file
                with open(json_path, 'w') as f:
                    json.dump(data, f, indent=2)
        else:
            typer.echo("No results found.")
        return
    
    if json_path:
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
            with open(json_path, 'w') as f:
                json.dump(data, f, indent=2)

    else:
        # Display table format to stdout
        _output_table(results, single, grouped)


def _output_table(results, single: bool = False, grouped: bool = False):
    """Output results in table format using PrettyTable."""
    # Handle None results
    if results is None:
        typer.echo("No results found.")
        return
        
    if single:
        # For single items, wrap in a list for consistent processing
        results = [results]
    
    if not results:
        typer.echo("No results found.")
        return
    
    # Handle grouped data specially
    if grouped:
        table = PrettyTable()
        table.field_names = ["Key", "Display Name", "Count"]
        table.max_width = MAX_WIDTH
        table.align = "l"
        
        for result in results:
            key = result.get('key', 'Unknown')
            display_name = result.get('key_display_name', key)
            count = result.get('count', 0)
            
            table.add_row([key, display_name, f"{count:,}"])
        
        typer.echo(table)
        return
    
    if not results:
        typer.echo("No results found.")
        return
    
    # Determine the type of entity based on the first result
    first_result = results[0]
    
    if 'publication_year' in first_result:  # Work
        table = PrettyTable()
        table.field_names = ["Name", "Year", "Journal", "Citations", "ID"]
        table.max_width = MAX_WIDTH
        table.align = "l"
        
        for result in results:
            title = (result.get('display_name') or result.get('title') or 
                    'Unknown')[:MAX_WIDTH]
            year = result.get('publication_year', 'N/A')
            
            journal = 'N/A'
            if 'primary_location' in result and result['primary_location']:
                source = result['primary_location'].get('source', {})
                if source and source.get('display_name'):
                    journal = (source.get('display_name') or 'N/A')[:30]
            
            citations = result.get('cited_by_count', 0)
            openalex_id = result.get('id', '').split('/')[-1]
            
            table.add_row([title, year, journal, citations, openalex_id])
            
    elif ('works_count' in first_result and 
          ('last_known_institutions' in first_result or 
           'last_known_institution' in first_result)):
        # Author
        table = PrettyTable()
        table.field_names = ["Name", "Works", "Citations", "Institution", "ID"]
        table.max_width = MAX_WIDTH
        table.align = "l"
        
        for result in results:
            name = (result.get('display_name') or 'Unknown')[:40]
            works = result.get('works_count', 0)
            citations = result.get('cited_by_count', 0)
            
            institution = 'N/A'
            # Handle new field (list) and old field (single object) for compatibility
            if result.get('last_known_institutions'):
                # New field: last_known_institutions is a list, take the first one
                institutions = result['last_known_institutions']
                if institutions and len(institutions) > 0:
                    inst = institutions[0]
                    institution = (inst.get('display_name') or 'Unknown')[:30]
            elif result.get('last_known_institution'):
                # Fallback for old field for backward compatibility
                inst = result['last_known_institution']
                institution = (inst.get('display_name') or 'Unknown')[:30]
            
            openalex_id = result.get('id', '').split('/')[-1]
            
            table.add_row([name, works, citations, institution, openalex_id])
    
    elif 'country_code' in first_result:  # Institution
        table = PrettyTable()
        table.field_names = ["Name", "Country", "Works", "Citations", "ID"]
        table.max_width = MAX_WIDTH
        table.align = "l"
        
        for result in results:
            name = (result.get('display_name') or 'Unknown')[:40]
            country = result.get('country_code', 'N/A')
            works = result.get('works_count', 0)
            citations = result.get('cited_by_count', 0)
            openalex_id = result.get('id', '').split('/')[-1]
            
            table.add_row([name, country, works, citations, openalex_id])
    
    elif 'issn' in first_result or 'issn_l' in first_result:  # Source/Journal
        table = PrettyTable()
        table.field_names = ["Name", "Type", "ISSN", "Works", "ID"]
        table.max_width = MAX_WIDTH
        table.align = "l"
        
        for result in results:
            name = (result.get('display_name') or 'Unknown')[:40]
            source_type = result.get('type', 'N/A')
            issn = result.get('issn_l', result.get('issn', ['N/A']))
            if isinstance(issn, list):
                issn = issn[0] if issn else 'N/A'
            works = result.get('works_count', 0)
            openalex_id = result.get('id', '').split('/')[-1]
            
            table.add_row([name, source_type, issn, works, openalex_id])
    
    elif 'hierarchy_level' in first_result:  # Publisher
        table = PrettyTable()
        table.field_names = ["Name", "Level", "Works", "Sources", "ID"]
        table.max_width = MAX_WIDTH
        table.align = "l"
        
        for result in results:
            name = (result.get('display_name') or 'Unknown')[:40]
            level = result.get('hierarchy_level', 'N/A')
            works = result.get('works_count', 0)
            sources = result.get('sources_count', 0)
            openalex_id = result.get('id', '').split('/')[-1]
            
            table.add_row([name, level, works, sources, openalex_id])
            
    elif 'works_count' in first_result:  # Topic, Domain, Field, Subfield, or Funder
        table = PrettyTable()
        table.field_names = ["Name", "Works", "Citations", "ID"]
        table.max_width = MAX_WIDTH
        table.align = "l"
        
        for result in results:
            name = (result.get('display_name') or 'Unknown')[
                :config.cli_name_truncate_length
            ]
            works = result.get('works_count', 0)
            citations = result.get('cited_by_count', 0)
            openalex_id = result.get('id', '').split('/')[-1]
            
            table.add_row([name, works, citations, openalex_id])
            
    else:  # Generic fallback
        table = PrettyTable()
        table.field_names = ["Name", "ID"]
        table.max_width = MAX_WIDTH
        table.align = "l"
        
        for result in results:
            name = (result.get('display_name') or result.get('title') or 
                   'Unknown')[:MAX_WIDTH]
            openalex_id = result.get('id', '').split('/')[-1]
            
            table.add_row([name, openalex_id])
    
    typer.echo(table)


def _output_grouped_results(results, json_path: Optional[str] = None):
    """Output grouped results in table format to stdout or JSON format to file/stdout."""
    if results is None:
        if json_path:
            data = []
            if json_path == "-":
                # Output JSON to stdout
                typer.echo(json.dumps(data, indent=2))
            else:
                # Save JSON to file
                with open(json_path, 'w') as f:
                    json.dump(data, f, indent=2)
        else:
            typer.echo("No grouped results found.")
        return
    
    # When group-by is used, the results list itself contains the grouped data
    grouped_data = results
    
    if not grouped_data:
        if json_path:
            data = []
            if json_path == "-":
                # Output JSON to stdout
                typer.echo(json.dumps(data, indent=2))
            else:
                # Save JSON to file
                with open(json_path, 'w') as f:
                    json.dump(data, f, indent=2)
        else:
            typer.echo("No grouped results found.")
        return
    
    if json_path:
        # Prepare JSON data
        data = [dict(item) for item in grouped_data]
        
        if json_path == "-":
            # Output JSON to stdout
            typer.echo(json.dumps(data, indent=2))
        else:
            # Save JSON to file
            with open(json_path, 'w') as f:
                json.dump(data, f, indent=2)
            typer.echo(f"Grouped results saved to {json_path}")
    else:
        # Display table format to stdout
        table = PrettyTable()
        table.field_names = ["Key", "Display Name", "Count"]
        table.max_width = MAX_WIDTH
        table.align = "l"
        
        for group in grouped_data:
            key = group.get('key', 'Unknown')
            display_name = group.get('key_display_name', key)
            count = group.get('count', 0)
            
            table.add_row([key, display_name, f"{count:,}"])
        
        typer.echo(table)
