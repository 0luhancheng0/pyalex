"""
Batch processing utilities for PyAlex CLI.

This module contains configurations and functions for handling large ID lists 
that need to be processed in batches for better performance and API compliance.
"""

import asyncio
import copy
from typing import List, Optional, Callable

import typer
from pyalex import config
from pyalex.core.config import MAX_PER_PAGE

# Global state - will be set by main CLI
_debug_mode = False
_dry_run_mode = False  
_batch_size = config.cli_batch_size


def set_global_state(debug_mode: bool, dry_run_mode: bool, batch_size: int):
    """Set global state from main CLI configuration."""
    global _debug_mode, _dry_run_mode, _batch_size
    _debug_mode = debug_mode
    _dry_run_mode = dry_run_mode
    _batch_size = batch_size


class BatchFilterConfig:
    """Configuration for handling large ID lists that need to be batched."""
    
    def __init__(self, filter_path, id_field="id", or_separator="|"):
        """
        Initialize batch filter configuration.
        
        Args:
            filter_path: Dot-separated path to the filter field (e.g., "grants.funder")
            id_field: Field name for the ID within the filter (default: "id")
            or_separator: Separator for OR logic in batch queries (default: "|")
        """
        self.filter_path = filter_path
        self.id_field = id_field
        self.or_separator = or_separator
    
    def apply_single_filter(self, query, id_value):
        """Apply filter for a single ID."""
        filter_dict = self._build_filter_dict(id_value)
        return query.filter(**filter_dict)
    
    def apply_batch_filter(self, query, id_list):
        """Apply filter for a batch of IDs using OR logic."""
        or_filter_value = self.or_separator.join(id_list)
        filter_dict = self._build_filter_dict(or_filter_value)
        return query.filter(**filter_dict)
    
    def _build_filter_dict(self, value):
        """Build nested filter dictionary from dot-separated path."""
        # Split path into parts (e.g., "grants.funder" -> ["grants", "funder"])
        path_parts = self.filter_path.split('.')
        
        # Build nested dict: {"grants": {"funder": value}} for path "grants.funder"
        result = {self.id_field: value}
        for part in reversed(path_parts):
            result = {part: result}
        
        return result
    
    def remove_from_params(self, params):
        """Remove this filter from query parameters to avoid conflicts."""
        if not params or 'filter' not in params:
            return
        
        current = params['filter']
        path_parts = self.filter_path.split('.')
        
        # Navigate to the parent of the target field
        for part in path_parts[:-1]:
            if part not in current:
                return
            current = current[part]
        
        # Remove the final field if it exists
        final_field = path_parts[-1]
        if final_field in current and self.id_field in current[final_field]:
            del current[final_field][self.id_field]


# Pre-configured batch filters for common use cases
BATCH_FILTER_CONFIGS = {
    # Works filters - using correct OpenAlex field names
    'works_funder': BatchFilterConfig("grants", "funder"),  # grants.funder (not grants.funder.id)
    'works_award': BatchFilterConfig("grants", "award_id"),  # grants.award_id
    'works_author': BatchFilterConfig("authorships.author", "id"),  # authorships.author.id
    'works_institution': BatchFilterConfig("authorships.institutions", "id"),  # authorships.institutions.id
    'works_source': BatchFilterConfig("primary_location.source", "id"),  # primary_location.source.id
    'works_topic': BatchFilterConfig("primary_topic", "id"),  # primary_topic.id
    'works_topics': BatchFilterConfig("topics", "id"),  # topics.id (all topics, not just primary)
    'works_subfield': BatchFilterConfig("primary_topic.subfield", "id"),  # primary_topic.subfield.id
    'works_cited_by': BatchFilterConfig("", "cited_by"),  # flat field: cited_by
    'works_cites': BatchFilterConfig("", "cites"),  # flat field: cites
    
    # Authors filters  
    'authors_institution': BatchFilterConfig("last_known_institutions", "id"),  # last_known_institutions.id
    
    # Topics filters
    'topics_domain': BatchFilterConfig("domain", "id"),  # domain.id
    'topics_field': BatchFilterConfig("field", "id"),  # field.id
    'topics_subfield': BatchFilterConfig("subfield", "id"),  # subfield.id
    
    # For future extensions
    'works_referenced_works': BatchFilterConfig("", "referenced_works"),  # For future use
    'authors_works': BatchFilterConfig("", "works"),  # For future use
    'institutions_works': BatchFilterConfig("", "works"),  # For future use
    'sources_works': BatchFilterConfig("", "works"),  # For future use
}


def register_batch_filter(filter_key, filter_path, id_field="id"):
    """
    Register a new batch filter configuration for easy extensibility.
    
    Args:
        filter_key: Key to use for the filter (e.g., 'works_source')
        filter_path: Dot-separated path to the filter field 
                    (e.g., 'primary_location.source')
        id_field: Field name for the ID within the filter (default: "id")
    
    Example:
        register_batch_filter('works_source', 'primary_location.source')
        register_batch_filter('works_cited_by', 'referenced_works')
    """
    BATCH_FILTER_CONFIGS[filter_key] = BatchFilterConfig(filter_path, id_field)


def _merge_grouped_results(batch_results_list):
    """
    Merge grouped results from multiple batches by aggregating counts.
    
    Args:
        batch_results_list: List of tuples (batch_results, batch_index)
        
    Returns:
        List of merged grouped results with aggregated counts
    """
    merged_counts = {}
    
    # Sort by batch index to maintain order
    batch_results_list.sort(key=lambda x: x[1])
    
    # Aggregate counts by key
    for batch_results, _ in batch_results_list:
        if batch_results:
            for result in batch_results:
                key = result.get('key')
                if key is not None:
                    if key in merged_counts:
                        # Sum the counts
                        merged_counts[key]['count'] += result.get('count', 0)
                    else:
                        # First occurrence - store the result
                        merged_counts[key] = {
                            'key': key,
                            'key_display_name': result.get('key_display_name', key),
                            'count': result.get('count', 0)
                        }
    
    # Convert back to list format, sorted by count (descending)
    return sorted(merged_counts.values(), key=lambda x: x['count'], reverse=True)


def _handle_large_id_list(
    query, 
    id_list, 
    filter_config_key, 
    entity_class,
    entity_name,
    all_results=False,
    limit=None,
    json_path=None
):
    """
    Generic handler for large ID lists that need to be processed in batches.
    
    Args:
        query: The base query object
        id_list: List of cleaned IDs
        filter_config_key: Key for the batch filter configuration
        entity_class: The entity class to create new queries
        entity_name: Human-readable entity name for progress reporting
        all_results: Whether to get all results
        limit: Result limit
        json_path: JSON output path
    
    Returns:
        Combined results from all batches
    """
    if filter_config_key not in BATCH_FILTER_CONFIGS:
        raise ValueError(f"Unknown filter config: {filter_config_key}")
    
    filter_config = BATCH_FILTER_CONFIGS[filter_config_key]
    
    def create_batch_query(batch_ids):
        """Create a query for a batch of IDs."""
        # Create a new query instance
        batch_query = entity_class()
        
        # Copy all parameters from the original query except the target filter
        if hasattr(query, 'params') and query.params:
            batch_query.params = copy.deepcopy(query.params)
            filter_config.remove_from_params(batch_query.params)
        
        # Apply the batch filter
        batch_query = filter_config.apply_batch_filter(batch_query, batch_ids)
        
        return batch_query
    
    # Use the existing batching utility (always uses async when available)
    return _execute_batched_queries(
        id_list,
        create_batch_query,
        entity_name,
        all_results,
        limit,
        json_path
    )


def _apply_id_list_filter(query, id_list, filter_config_key, entity_class):
    """
    Apply filter for an ID list, handling both small and large lists.
    
    Args:
        query: The query object to modify
        id_list: List of IDs (already cleaned)
        filter_config_key: Key for the batch filter configuration
        entity_class: The entity class (for large list handling)
    
    Returns:
        Modified query object, or original query with a special attribute for 
        large lists
    """
    if filter_config_key not in BATCH_FILTER_CONFIGS:
        raise ValueError(f"Unknown filter config: {filter_config_key}")
    
    filter_config = BATCH_FILTER_CONFIGS[filter_config_key]
    
    if len(id_list) == 1:
        # Single ID
        return filter_config.apply_single_filter(query, id_list[0])
    elif len(id_list) <= _batch_size:
        # Small list - use OR logic in single query
        return filter_config.apply_batch_filter(query, id_list)
    else:
        # Large list - mark for batch processing
        setattr(query, f'_large_{filter_config_key}_list', id_list)
        return query


def add_id_list_option_to_command(
    query, option_value, filter_config_key, entity_class
):
    """
    Helper function to easily add ID list handling to any command.
    
    Args:
        query: The query object
        option_value: The comma-separated string of IDs from the CLI option
        filter_config_key: The filter configuration key
        entity_class: The entity class for large list handling
    
    Returns:
        Modified query object
    
    Example usage in a command:
        # For works command with author IDs:
        if author_ids:
            query = add_id_list_option_to_command(
                query, author_ids, 'works_author', Works
            )
        
        # For works command with cited_by IDs (future):
        if cited_by_ids:
            query = add_id_list_option_to_command(
                query, cited_by_ids, 'works_cited_by', Works
            )
        
        # For institutions command with works IDs (future):
        if works_ids:
            query = add_id_list_option_to_command(
                query, works_ids, 'institutions_works', Institutions
            )
    """
    if not option_value:
        return query
    
    # Import here to avoid circular imports
    from .utils import _clean_ids
    
    # Parse comma-separated IDs
    id_list = [
        aid.strip() for aid in option_value.split(',') if aid.strip()
    ]
    # Clean up IDs (remove URL prefix if present)
    cleaned_id_list = _clean_ids(id_list)
    
    # Apply the filter
    return _apply_id_list_filter(
        query, cleaned_id_list, filter_config_key, entity_class
    )


def _execute_batched_queries(
    id_list, 
    create_query_func,
    entity_name,
    all_results=False,
    limit=None,
    json_path=None
):
    """
    Execute batched queries for large lists of IDs using async by default.
    Always attempts to use async for better performance.
    
    Args:
        id_list: List of cleaned IDs to process in batches
        create_query_func: Function that takes a list of batch IDs and returns a query
        entity_name: Human-readable name for debug output
        all_results: Whether to get all results
        limit: Result limit
        json_path: JSON output path
    
    Returns:
        Combined results from all batches
    """
    # Always try to use async for improved performance
    try:
        # Check if we're already in an async context
        try:
            asyncio.get_running_loop()
            # We're in an async context, but we can't use await here
            # Fall back to sync
            return _sync_execute_batched_queries(
                id_list, create_query_func, entity_name, all_results, limit, json_path
            )
        except RuntimeError:
            # No running loop, we can create one
            return asyncio.run(_async_execute_batched_queries(
                id_list, create_query_func, entity_name, all_results, limit, json_path
            ))
    except ImportError:
        # asyncio not available, use sync
        return _sync_execute_batched_queries(
            id_list, create_query_func, entity_name, all_results, limit, json_path
        )


async def _async_execute_batched_queries(
    id_list,
    create_query_func,
    entity_name,
    all_results=False,
    limit=None,
    json_path=None
):
    """
    Execute batched queries asynchronously with two-level progress display.
    
    Level 1: Batch processing progress (top-level)
    Level 2: Individual query pagination progress (nested under each batch)
    
    Args:
        id_list: List of cleaned IDs to process in batches
        create_query_func: Function that takes a list of batch IDs and returns a query
        entity_name: Human-readable name for debug output
        all_results: Whether to get all results
        limit: Result limit
        json_path: JSON output path
    
    Returns:
        Combined results from all batches
    """
    # Import here to avoid circular imports
    from .utils import _print_dry_run_query, _add_abstract_to_work
    
    if _dry_run_mode:
        estimated_queries = (len(id_list) + _batch_size - 1) // _batch_size
        _print_dry_run_query(
            f"Async batched query for {len(id_list)} {entity_name}",
            estimated_queries=estimated_queries
        )
        return None
    
    num_batches = (len(id_list) + _batch_size - 1) // _batch_size
    
    if not json_path:
        typer.echo(
            f"Processing {len(id_list)} {entity_name} "
            f"in {num_batches} batches (async)...", 
            err=True
        )
    
    # Import Rich Progress components
    try:
        from rich.progress import (
            BarColumn, Progress, SpinnerColumn, TextColumn, 
            MofNCompleteColumn, TimeElapsedColumn
        )
        from rich.live import Live
        from rich.console import Group
        use_rich = True
    except ImportError:
        use_rich = False
    
    if not use_rich or json_path:
        # Fall back to single-level progress if Rich unavailable or saving JSON
        return await _async_execute_batched_queries_simple(
            id_list, create_query_func, entity_name, all_results, limit, json_path
        )
    
    # Create multi-level progress display
    overall_progress = Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
    )
    
    batch_progress = Progress(
        TextColumn("  ├─ [bold green]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
    )
    
    progress_group = Group(overall_progress, batch_progress)
    
    # Track batch results
    batch_results_list = []
    
    # Process batches with two-level progress display
    async def process_single_batch_with_progress(batch_ids, batch_index, main_task_id):
        """Process a single batch with nested progress tracking."""
        batch_query = create_query_func(batch_ids)
        
        if _debug_mode:
            typer.echo(
                f"[DEBUG] Batch {batch_index + 1} query: {batch_query.url}", 
                err=True
            )
        
        # Check if this batch needs pagination (for Level 2 progress)
        needs_pagination = False
        batch_task_id = None
        
        try:
            # Get count to determine if we need Level 2 progress
            if all_results or (limit and limit > MAX_PER_PAGE):
                count_result = batch_query.get(per_page=1)
                total_count = count_result.meta.get('count', 0)
                
                # Show individual progress if we have significant results
                if total_count > 200 and total_count <= 10000:
                    needs_pagination = True
                    batch_task_id = batch_progress.add_task(
                        f"Batch {batch_index + 1}: Fetching {total_count} results",
                        total=total_count
                    )
        except Exception:
            # If count fails, proceed without Level 2 progress
            pass
        
        # Execute the batch query
        if needs_pagination and batch_task_id is not None:
            # Use async pagination with progress updates
            batch_results = await _get_async_with_progress(
                batch_query, batch_progress, batch_task_id, limit=limit
            )
        else:
            # Use simple async execution
            if all_results:
                batch_results = await _get_async_without_progress(
                    batch_query, limit=None
                )
            elif limit is not None:
                batch_results = await _get_async_without_progress(
                    batch_query, limit=limit
                )
            else:
                batch_results = await _get_async_without_progress(batch_query)
        
        # Clean up Level 2 progress task
        if batch_task_id is not None:
            batch_progress.remove_task(batch_task_id)
        
        # Update Level 1 progress
        overall_progress.update(main_task_id, advance=1)
        
        if _debug_mode:
            batch_count = len(batch_results) if batch_results else 0
            typer.echo(
                f"[DEBUG] Batch {batch_index + 1} returned {batch_count} results", 
                err=True
            )
        
        return batch_results, batch_index
    
    # Execute with live progress display
    with Live(progress_group, refresh_per_second=10):
        # Add main progress task
        main_task_id = overall_progress.add_task(
            f"Processing {entity_name} batches", 
            total=num_batches
        )
        
        # Create batch processing tasks
        batch_tasks = []
        for i in range(0, len(id_list), _batch_size):
            batch_ids = id_list[i:i + _batch_size]
            batch_index = i // _batch_size
            task = process_single_batch_with_progress(batch_ids, batch_index, main_task_id)
            batch_tasks.append(task)
        
        # Process batches with limited concurrency
        max_concurrent = min(config.max_concurrent or 5, len(batch_tasks))
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def limited_batch_process(batch_task):
            async with semaphore:
                return await batch_task
        
        limited_tasks = [limited_batch_process(task) for task in batch_tasks]
        batch_results_list = await asyncio.gather(*limited_tasks)
    
    # Combine all results and remove duplicates or merge grouped results
    # Check if this is a grouped query by examining the first batch query
    has_group_by = False
    if batch_results_list:
        test_query = create_query_func([])  # Create empty query to check params
        has_group_by = (hasattr(test_query, 'params') and test_query.params and 
                        'group-by' in test_query.params)
    
    if has_group_by:
        # Handle grouped results - merge by key and sum counts
        combined_results = _merge_grouped_results(batch_results_list)
    else:
        # Handle regular entity results - deduplicate by ID
        combined_results = []
        seen_ids = set()
        
        # Sort by batch index to maintain order
        batch_results_list.sort(key=lambda x: x[1])
        
        for batch_results, _ in batch_results_list:
            if batch_results:
                # Filter out duplicates based on entity ID
                for entity in batch_results:
                    entity_id_str = entity.get('id')
                    if entity_id_str and entity_id_str not in seen_ids:
                        seen_ids.add(entity_id_str)
                        combined_results.append(entity)
    
    # Convert abstracts for works if needed
    if 'works' in entity_name.lower():
        combined_results = [_add_abstract_to_work(work) for work in combined_results]
    
    # Create a result object similar to what query.get() returns
    if combined_results:
        from pyalex.core.response import OpenAlexResponseList
        results = OpenAlexResponseList(
            combined_results, {"count": len(combined_results)}, dict
        )
    else:
        from pyalex.core.response import OpenAlexResponseList
        results = OpenAlexResponseList(
            [], {"count": 0}, dict
        )
    
    if not json_path:
        typer.echo(
            f"Combined {len(combined_results)} unique results from "
            f"{len(id_list)} {entity_name} (async)", 
            err=True
        )
    
    return results


async def _get_async_with_progress(query, progress_obj, task_id, limit=None):
    """
    Async query execution with progress updates for Level 2 progress tracking.
    
    This function updates the provided progress object and task ID as it fetches results.
    """
    from pyalex.client.async_session import async_batch_requests
    
    # Get count first to set up pagination
    count_result = query.get(per_page=1)
    total_count = count_result.meta.get('count', 0)
    
    # Determine effective limit for processing
    effective_limit = min(limit or total_count, total_count)
    
    if effective_limit <= MAX_PER_PAGE:
        # Single page request
        result = query.get(limit=effective_limit)
        progress_obj.update(task_id, completed=effective_limit)
        return result
    
    # Multi-page async processing with progress updates
    effective_per_page = MAX_PER_PAGE
    
    # Check if this is a group-by query
    has_group_by = (hasattr(query, 'params') and query.params and 
                    isinstance(query.params, dict) and 'group-by' in query.params)
    
    if has_group_by:
        # For group-by operations, only page 1 is supported (max 200 results)
        page_query = query.__class__(query.params.copy())
        page_query._add_params("per-page", 200)
        urls = [page_query.url]
        # Update effective_limit for group-by
        effective_limit = min(200, effective_limit)
    else:
        num_pages = (effective_limit + effective_per_page - 1) // effective_per_page
        
        # Create URLs for all pages
        urls = []
        for page_num in range(1, num_pages + 1):
            params_copy = (
                query.params.copy() if isinstance(query.params, dict) 
                else query.params
            )
            page_query = query.__class__(params_copy)
            page_query._add_params("per-page", effective_per_page)
            page_query._add_params("page", page_num)
            urls.append(page_query.url)
    
    # Execute async requests with progress updates
    all_results = []
    final_meta = {}
    max_concurrent = min(config.max_concurrent or 10, len(urls))
    
    # Process pages in smaller batches to update progress more frequently
    batch_size = max(1, max_concurrent // 2)
    
    for i in range(0, len(urls), batch_size):
        batch_urls = urls[i:i + batch_size]
        responses = await async_batch_requests(batch_urls, max_concurrent=max_concurrent)
        
        # Process responses and update progress
        for response_data in responses:
            if 'group_by' in response_data:
                # For group-by queries, data is in 'group_by' field
                batch_results = response_data['group_by']
                all_results.extend(batch_results)
                if not final_meta and 'meta' in response_data:
                    final_meta = response_data['meta'].copy()
                
                # Update progress with actual results fetched
                progress_obj.update(task_id, advance=len(batch_results))
            elif 'results' in response_data:
                batch_results = response_data['results']
                all_results.extend(batch_results)
                if not final_meta and 'meta' in response_data:
                    final_meta = response_data['meta'].copy()
                
                # Update progress with actual results fetched
                progress_obj.update(task_id, advance=len(batch_results))
    
    # Trim to exact limit if specified
    if limit and len(all_results) > limit:
        all_results = all_results[:limit]
    
    # Update meta count
    final_meta['count'] = len(all_results)
    
    # Create response object
    from pyalex.core.response import OpenAlexResponseList
    return OpenAlexResponseList(
        all_results, final_meta, query.resource_class
    )


async def _async_execute_batched_queries_simple(
    id_list,
    create_query_func,
    entity_name,
    all_results=False,
    limit=None,
    json_path=None
):
    """
    Simple single-level async execution (fallback when Rich is unavailable).
    """
    from .utils import _add_abstract_to_work
    
    # This is the original implementation without multi-level progress
    num_batches = (len(id_list) + _batch_size - 1) // _batch_size
    
    async def process_single_batch(batch_ids, batch_index):
        batch_query = create_query_func(batch_ids)
        
        if all_results:
            batch_results = await _get_async_without_progress(
                batch_query, limit=None
            )
        elif limit is not None:
            batch_results = await _get_async_without_progress(
                batch_query, limit=limit
            )
        else:
            batch_results = await _get_async_without_progress(batch_query)
        
        return batch_results, batch_index
    
    # Create and execute tasks
    batch_tasks = []
    for i in range(0, len(id_list), _batch_size):
        batch_ids = id_list[i:i + _batch_size]
        batch_index = i // _batch_size
        task = process_single_batch(batch_ids, batch_index)
        batch_tasks.append(task)
    
    max_concurrent = min(config.max_concurrent or 5, len(batch_tasks))
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def limited_batch_process(batch_task):
        async with semaphore:
            return await batch_task
    
    limited_tasks = [limited_batch_process(task) for task in batch_tasks]
    batch_results_list = await asyncio.gather(*limited_tasks)
    
    # Combine results and handle grouped vs entity results
    # Check if this is a grouped query by examining the first batch query
    has_group_by = False
    if batch_results_list:
        test_query = create_query_func([])  # Create empty query to check params
        has_group_by = (hasattr(test_query, 'params') and test_query.params and 
                        'group-by' in test_query.params)
    
    if has_group_by:
        # Handle grouped results - merge by key and sum counts
        combined_results = _merge_grouped_results(batch_results_list)
    else:
        # Handle regular entity results - deduplicate by ID
        combined_results = []
        seen_ids = set()
        
        batch_results_list.sort(key=lambda x: x[1])
        
        for batch_results, _ in batch_results_list:
            if batch_results:
                for entity in batch_results:
                    entity_id_str = entity.get('id')
                    if entity_id_str and entity_id_str not in seen_ids:
                        seen_ids.add(entity_id_str)
                        combined_results.append(entity)
    
    # Convert abstracts for works if needed
    if 'works' in entity_name.lower():
        combined_results = [_add_abstract_to_work(work) for work in combined_results]
    
    # Create result object
    if combined_results:
        from pyalex.core.response import OpenAlexResponseList
        results = OpenAlexResponseList(
            combined_results, {"count": len(combined_results)}, dict
        )
    else:
        from pyalex.core.response import OpenAlexResponseList
        results = OpenAlexResponseList(
            [], {"count": 0}, dict
        )
    
    return results


async def _get_async_without_progress(query, limit=None):
    """
    Async query execution without progress bars to avoid conflicts.
    
    This is used for Level 2 async processing when Level 1 progress is active.
    """
    from pyalex.client.async_session import async_batch_requests
    
    # For single entity retrieval or small limits, use sync method
    if isinstance(query.params, str) or (limit and limit <= MAX_PER_PAGE):
        return query.get(limit=limit)
    
    # Get count first to decide on pagination strategy
    count_result = query.get(per_page=1)
    total_count = count_result.meta.get('count', 0)
    
    # Determine effective limit for async decision
    effective_limit = limit if limit is not None else total_count
    
    # Use async if either total count ≤ 10,000 OR user limit ≤ 10,000
    if total_count <= 10000 or effective_limit <= 10000:
        # Check if this is a group-by query
        has_group_by = (hasattr(query, 'params') and query.params and 
                        isinstance(query.params, dict) and 'group-by' in query.params)
        
        if has_group_by:
            # For group-by operations, only page 1 is supported (max 200 results)
            page_query = query.__class__(query.params.copy())
            page_query._add_params("per-page", 200)
            urls = [page_query.url]
        else:
            # Use async basic paging without progress
            effective_per_page = MAX_PER_PAGE
            effective_limit = min(limit or total_count, total_count)
            
            # Calculate number of pages needed
            num_pages = (effective_limit + effective_per_page - 1) // effective_per_page
            
            # Create URLs for all pages
            urls = []
            for page_num in range(1, num_pages + 1):
                # Create a copy of query with page parameters
                params_copy = (
                    query.params.copy() if isinstance(query.params, dict) 
                    else query.params
                )
                page_query = query.__class__(params_copy)
                page_query._add_params("per-page", effective_per_page)
                page_query._add_params("page", page_num)
                urls.append(page_query.url)
        
        # Execute async requests without progress tracking
        max_concurrent = min(config.max_concurrent or 10, len(urls))
        responses = await async_batch_requests(urls, max_concurrent=max_concurrent)
        
        # Combine results
        all_results = []
        final_meta = {}
        
        for response_data in responses:
            if 'group_by' in response_data:
                # For group-by queries, data is in 'group_by' field
                all_results.extend(response_data['group_by'])
                if not final_meta and 'meta' in response_data:
                    final_meta = response_data['meta'].copy()
            elif 'results' in response_data:
                all_results.extend(response_data['results'])
                if not final_meta and 'meta' in response_data:
                    final_meta = response_data['meta'].copy()
        
        # Trim to exact limit if specified
        if limit and len(all_results) > limit:
            all_results = all_results[:limit]
        
        # Update meta count
        final_meta['count'] = len(all_results)
        
        # Create response object
        from pyalex.core.response import OpenAlexResponseList
        return OpenAlexResponseList(
            all_results, final_meta, query.resource_class
        )
    else:
        # Use sync for larger datasets
        return query.get(limit=limit)


def _sync_execute_batched_queries(
    id_list, 
    create_query_func,
    entity_name,
    all_results=False,
    limit=None,
    json_path=None
):
    """
    Synchronous fallback for batched queries (original implementation).
    
    Args:
        id_list: List of cleaned IDs to process in batches
        create_query_func: Function that takes a list of batch IDs and returns a query
        entity_name: Human-readable name for debug output
        all_results: Whether to get all results
        limit: Result limit
        json_path: JSON output path
    
    Returns:
        Combined results from all batches
    """
    from .utils import _print_dry_run_query, _add_abstract_to_work, _paginate_with_progress
    
    if _dry_run_mode:
        estimated_queries = (len(id_list) + _batch_size - 1) // _batch_size
        _print_dry_run_query(
            f"Batched query for {len(id_list)} {entity_name}",
            estimated_queries=estimated_queries
        )
        return None
    
    if not json_path:
        typer.echo(
            f"Processing {len(id_list)} {entity_name} "
            f"in batches of {_batch_size}...", 
            err=True
        )
    
    # Check if this is a grouped query by examining a test query
    has_group_by = False
    if id_list:
        test_query = create_query_func([])  # Create empty query to check params
        has_group_by = (hasattr(test_query, 'params') and test_query.params and 
                        'group-by' in test_query.params)
    
    if has_group_by:
        # For grouped queries, collect all results for merging
        batch_results_list = []
    else:
        # For entity queries, use deduplication
        combined_results = []
        seen_ids = set()  # To avoid duplicates
    
    for i in range(0, len(id_list), _batch_size):
        batch_ids = id_list[i:i + _batch_size]
        batch_index = i // _batch_size
        
        if _debug_mode:
            from pyalex.logger import get_logger
            logger = get_logger()
            logger.debug(
                f"Processing batch "
                f"{i//_batch_size + 1}: {len(batch_ids)} {entity_name}"
            )
        
        # Create query for this batch
        batch_query = create_query_func(batch_ids)
        
        if _debug_mode:
            typer.echo(
                f"[DEBUG] Batch API URL: {batch_query.url}", 
                err=True
            )
        
        # Execute the batch query
        if all_results:
            # Get all results for this batch using pagination with progress bar
            batch_name = f"{entity_name} (batch {i//_batch_size + 1})"
            batch_results = _paginate_with_progress(batch_query, batch_name)
        elif limit is not None:
            batch_results = batch_query.get(limit=limit)
        else:
            batch_results = batch_query.get()  # Default first page
        
        if batch_results:
            if has_group_by:
                # Store results for later merging
                batch_results_list.append((batch_results, batch_index))
            else:
                # Filter out duplicates based on entity ID
                for entity in batch_results:
                    entity_id_str = entity.get('id')
                    if entity_id_str and entity_id_str not in seen_ids:
                        seen_ids.add(entity_id_str)
                        combined_results.append(entity)
        
        if _debug_mode:
            batch_count = len(batch_results) if batch_results else 0
            typer.echo(
                f"[DEBUG] Batch {i//_batch_size + 1} returned "
                f"{batch_count} results", 
                err=True
            )
    
    # Merge results after all batches are processed
    if has_group_by:
        combined_results = _merge_grouped_results(batch_results_list)
    
    # Create a result object similar to what query.get() returns
    # Import the appropriate response class based on the first result
    if combined_results:
        from pyalex.core.response import OpenAlexResponseList
        results = OpenAlexResponseList(
            combined_results, {"count": len(combined_results)}, dict
        )
    else:
        from pyalex.core.response import OpenAlexResponseList
        results = OpenAlexResponseList(
            [], {"count": 0}, dict
        )
    
    if not json_path:
        typer.echo(
            f"Combined {len(combined_results)} unique results from "
            f"{len(id_list)} {entity_name}", 
            err=True
        )
    
    return results
