#!/usr/bin/env python3
import copy
import datetime
import json
import os
import sys
from typing import Optional

import typer
from prettytable import PrettyTable
from typing_extensions import Annotated

from pyalex import Authors
from pyalex import Domains
from pyalex import Fields
from pyalex import Funders
from pyalex import Institutions
from pyalex import Keywords
from pyalex import Publishers
from pyalex import Sources
from pyalex import Subfields
from pyalex import Topics
from pyalex import Works
from pyalex import config
from pyalex import invert_abstract
from pyalex.core.config import MAX_PER_PAGE


# Configuration for handling large ID lists and batch filters
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
        return filter_config.apply_batch_filter(batch_query, batch_ids)
    
    # Use the existing batching utility
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


# Global verbose state
_debug_mode = False
_dry_run_mode = False
_batch_size = config.cli_batch_size

MAX_WIDTH = config.cli_max_width

app = typer.Typer(
    name="pyalex",
    help="CLI interface for the OpenAlex database",
    no_args_is_help=True,
)

# Global options


@app.callback()
def main(
    debug: Annotated[bool, typer.Option(
        "--debug", "-d",
        help="Enable debug output including API URLs and internal details"
    )] = False,
    dry_run: Annotated[bool, typer.Option(
        "--dry-run",
        help="Print a list of queries that would be run without executing them"
    )] = False,
    batch_size: Annotated[int, typer.Option(
        "--batch-size",
        help=f"Batch size for requests with multiple IDs "
             f"(default: {config.cli_batch_size})"
    )] = config.cli_batch_size,
):
    """
    PyAlex CLI - Access the OpenAlex database from the command line.
    
    OpenAlex doesn't require authentication for most requests.
    """
    global _debug_mode, _dry_run_mode, _batch_size
    _debug_mode = debug
    _dry_run_mode = dry_run
    _batch_size = batch_size
    
    if debug:
        from pyalex.logger import setup_cli_logging
        logger = setup_cli_logging(debug=True)
        logger.debug(f"Email: {config.email}")
        logger.debug(f"User Agent: {config.user_agent}")
        logger.debug(
            "Debug mode enabled - API URLs and internal details will be displayed"
        )
    
    if dry_run:
        typer.echo(f"Dry run mode enabled - batch size: {batch_size}", err=True)


def _print_debug_url(query):
    """Print the constructed URL for debugging when verbose mode is enabled."""
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
    """Handle CLI exceptions with optional debug logging."""
    if _debug_mode:
        from pyalex.logger import get_logger
        logger = get_logger()
        logger.debug("Full traceback:", exc_info=True)
    typer.echo(f"Error: {e}", err=True)
    raise typer.Exit(1) from e


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
    """Async function to retrieve entities by IDs using batch requests."""
    try:
        from pyalex.client.async_session import async_batch_requests
    except ImportError:
        # Fall back to sync processing if aiohttp not available
        return _sync_retrieve_entities(entity_class, ids, class_name)
    
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
    
    # Execute async requests
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


def _sync_retrieve_entities(entity_class, ids, class_name):
    """Sync fallback for entity retrieval."""
    all_results = []
    
    # Process IDs in batches using configurable batch size
    for i in range(0, len(ids), _batch_size):
        batch_ids = ids[i:i + _batch_size]
        
        if len(batch_ids) == 1:
            # Single ID - use direct retrieval
            batch_results = entity_class()[batch_ids[0]]
            if not isinstance(batch_results, list):
                batch_results = [batch_results]
        else:
            # Multiple IDs - use OR operator for batch retrieval
            id_filter = "|".join(batch_ids)
            batch_results = entity_class().filter(openalex_id=id_filter).get()
        
        # Handle results
        if batch_results:
            # Convert abstracts for works if requested
            if class_name == 'Works':
                batch_results = [
                    _add_abstract_to_work(work) for work in batch_results
                ]
            
            all_results.extend(batch_results)
        
        if _debug_mode and len(ids) > _batch_size:
            typer.echo(
                f"[DEBUG] Processed batch {i//_batch_size + 1} "
                f"({len(batch_ids)} IDs)", 
                err=True
            )
    
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


def _execute_query_with_options(query, all_results, limit, entity_name):
    """
    Execute a query based on the specified options.
    
    Args:
        query: OpenAlex query object
        all_results: Whether to get all results (with progress bar)
        limit: Result limit
        entity_name: Entity type name for progress bar
    
    Returns:
        Query results
    """
    if all_results:
        return _paginate_with_progress(query, entity_name)
    elif limit is not None:
        return query.get(limit=limit)
    else:
        return query.get()  # Default first page


def _paginate_with_progress(query, entity_type_name="results"):
    """
    Paginate through all results with a progress bar.
    Uses async pagination for datasets <= 10,000 results, sync for larger.
    
    Args:
        query: OpenAlex query object
        entity_type_name: String name for the entity type for the progress bar
    
    Returns:
        OpenAlexResponseList of all results
    """
    import asyncio
    
    # Check if async is available and get total count
    try:
        count_result = query.get(per_page=1)
        total_count = count_result.meta.get('count', 0)
        
        # Use async for smaller datasets
        if total_count <= 10000:
            try:
                return asyncio.run(
                    _async_paginate_with_progress(query, entity_type_name, total_count)
                )
            except ImportError:
                # Fall back to sync if aiohttp not available
                pass
    except Exception:
        # If count fails, fall back to sync pagination
        pass
    
    # Sync pagination fallback
    return _sync_paginate_with_progress(query, entity_type_name)


async def _async_paginate_with_progress(query, entity_type_name, total_count):
    """Async pagination with progress bar."""
    try:
        result = await query.get_async(limit=total_count)
        return result
    except AttributeError:
        # Fall back to sync if get_async not available
        return _sync_paginate_with_progress(query, entity_type_name)


def _execute_query_smart(query, all_results=False, limit=None):
    """Execute query using the best method (async or sync) based on conditions."""
    if all_results:
        # Get all results using pagination with progress bar
        return _paginate_with_progress(query, "query")
    elif limit is not None:
        # Check if we should use async for this limit
        if query.should_use_async(limit):
            # Use async execution
            import asyncio
            try:
                async def _run_query():
                    return await query.get_async(limit=limit)
                return asyncio.run(_run_query())
            except ImportError:
                # aiohttp not available, fall back to sync
                return query.get(limit=limit)
        else:
            return query.get(limit=limit)
    else:
        return query.get()  # Default first page


def _sync_paginate_with_progress(query, entity_type_name):
    """Sync pagination with progress bar (original implementation)."""
    try:
        from rich.progress import (
            Progress, SpinnerColumn, TextColumn, BarColumn, 
            MofNCompleteColumn, TimeElapsedColumn
        )
        use_rich = True
    except ImportError:
        from tqdm import tqdm
        use_rich = False
    
    # Use the paginate method directly to get all results
    # Start with cursor pagination to get the total count
    paginator = query.paginate(
        method="cursor", 
        cursor="*", 
        per_page=MAX_PER_PAGE
    )
    
    all_results = []
    total_count = None
    progress_bar = None
    progress = None
    task_id = None
    
    try:
        if use_rich:
            progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                MofNCompleteColumn(),
                TimeElapsedColumn(),
            )
            progress.start()
        
        for i, batch in enumerate(paginator):
            if not batch:
                break
                
            # Set up progress bar after first batch when we know the total
            if (i == 0 and hasattr(batch, 'meta') and 
                batch.meta and 'count' in batch.meta):
                total_count = batch.meta['count']
                progress_desc = f"Fetching {entity_type_name}"
                
                if use_rich:
                    task_id = progress.add_task(progress_desc, total=total_count)
                else:
                    progress_bar = tqdm(
                        total=total_count,
                        desc=progress_desc,
                        unit=" results",
                        initial=0
                    )
            
            all_results.extend(batch)
            
            if use_rich and task_id is not None:
                progress.update(task_id, advance=len(batch))
            elif progress_bar:
                progress_bar.update(len(batch))
                
            # Stop if we've collected enough results
            if total_count and len(all_results) >= total_count:
                break
                
    finally:
        if use_rich and progress:
            progress.stop()
        elif progress_bar:
            progress_bar.close()
    
    # Create a result object similar to what query.get() returns
    if all_results:
        from pyalex.core.response import OpenAlexResponseList
        # Use the same resource classes as the first batch
        first_batch = next(iter([batch for batch in [all_results[:1]] if batch]), None)
        if first_batch and hasattr(first_batch[0], '__class__'):
            # Try to get resource class from the results structure
            resource_class = getattr(paginator.endpoint_class, 'resource_class', None)
            resource_entity_class = getattr(
                paginator.endpoint_class, 'resource_entity_class', None
            )
        else:
            resource_class = None
            resource_entity_class = None
            
        return OpenAlexResponseList(
            all_results, 
            {"count": len(all_results)}, 
            resource_class,
            resource_entity_class
        )
    else:
        from pyalex.core.response import OpenAlexResponseList
        return OpenAlexResponseList([], {"count": 0})


def _execute_batched_queries(
    id_list, 
    create_query_func,
    entity_name,
    all_results=False,
    limit=None,
    json_path=None
):
    """
    Execute batched queries for large lists of IDs using a query creation function.
    
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
    
    combined_results = []
    seen_ids = set()  # To avoid duplicates
    
    for i in range(0, len(id_list), _batch_size):
        batch_ids = id_list[i:i + _batch_size]
        
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




def _add_abstract_to_work(work_dict):
    """Convert inverted abstract index to readable abstract for a work."""
    if (isinstance(work_dict, dict) and 
        'abstract_inverted_index' in work_dict and 
        work_dict['abstract_inverted_index'] is not None):
        work_dict['abstract'] = invert_abstract(work_dict['abstract_inverted_index'])
    return work_dict


def _output_results(results, json_path: Optional[str] = None, single: bool = False):
    """Output results in table format to stdout or JSON format to file."""
    # Handle None or empty results
    if results is None:
        if json_path:
            with open(json_path, 'w') as f:
                json.dump([], f, indent=2)
        else:
            typer.echo("No results found.")
        return
    
    if not single and (not results or len(results) == 0):
        if json_path:
            with open(json_path, 'w') as f:
                json.dump([], f, indent=2)
        else:
            typer.echo("No results found.")
        return
    
    if json_path:
        # Save JSON to file
        if single:
            data = dict(results)
        else:
            data = [dict(r) for r in results]
        
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2)

    else:
        # Display table format to stdout
        _output_table(results, single)


def _output_table(results, single: bool = False):
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
    """Output grouped results in table format to stdout or JSON format to file."""
    if results is None:
        if json_path:
            with open(json_path, 'w') as f:
                json.dump([], f, indent=2)
        else:
            typer.echo("No grouped results found.")
        return
    
    # When group-by is used, the results list itself contains the grouped data
    grouped_data = results
    
    if not grouped_data:
        if json_path:
            with open(json_path, 'w') as f:
                json.dump([], f, indent=2)
        else:
            typer.echo("No grouped results found.")
        return
    
    if json_path:
        # Save JSON to file
        with open(json_path, 'w') as f:
            json.dump([dict(item) for item in grouped_data], f, indent=2)
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


@app.command()
def works(
    search: Annotated[Optional[str], typer.Option(
        "--search", "-s",
        help="Search term for works"
    )] = None,
    author_ids: Annotated[Optional[str], typer.Option(
        "--author-ids",
        help="Filter by author OpenAlex ID(s). Use comma-separated values for "
             "OR logic (e.g., --author-ids 'A123,A456,A789')"
    )] = None,
    institution_ids: Annotated[Optional[str], typer.Option(
        "--institution-ids", 
        help="Filter by institution OpenAlex ID(s). Use comma-separated values for "
             "OR logic (e.g., --institution-ids 'I123,I456,I789')"
    )] = None,
    publication_year: Annotated[Optional[str], typer.Option(
        "--year",
        help="Filter by publication year (e.g. '2020' or range '2019:2021')"
    )] = None,
    publication_date: Annotated[Optional[str], typer.Option(
        "--date",
        help="Filter by publication date (e.g. '2020-01-01' or "
             "range '2019-01-01:2020-12-31')"
    )] = None,
    work_type: Annotated[Optional[str], typer.Option(
        "--type",
        help="Filter by work type (e.g. 'article', 'book', 'dataset')"
    )] = None,
    topic_ids: Annotated[Optional[str], typer.Option(
        "--topic-ids",
        help="Filter by primary topic OpenAlex ID(s). Use comma-separated values for "
             "OR logic (e.g., --topic-ids 'T123,T456,T789')"
    )] = None,
    subfield_ids: Annotated[Optional[str], typer.Option(
        "--subfield-ids",
        help="Filter by primary topic subfield OpenAlex ID(s). Use comma-separated values for "
             "OR logic (e.g., --subfield-ids 'SF123,SF456,SF789')"
    )] = None,
    funder_ids: Annotated[Optional[str], typer.Option(
        "--funder-ids",
        help="Filter by funder OpenAlex ID(s). Use comma-separated values for "
             "OR logic (e.g., --funder-ids 'F123,F456,F789')"
    )] = None,
    award_ids: Annotated[Optional[str], typer.Option(
        "--award-ids",
        help="Filter by grant award ID(s). Use comma-separated values for "
             "OR logic (e.g., --award-ids 'AWARD123,AWARD456')"
    )] = None,
    group_by: Annotated[Optional[str], typer.Option(
        "--group-by",
        help="Group results by field (e.g. 'oa_status', 'publication_year', "
             "'type', 'is_retracted', 'cited_by_count')"
    )] = None,
    all_results: Annotated[bool, typer.Option(
        "--all",
        help="Retrieve all results (default: first page only)"
    )] = False,
    limit: Annotated[Optional[int], typer.Option(
        "--limit", "-l",
        help="Maximum number of results to return (mutually exclusive with --all)"
    )] = None,
    json_path: Annotated[Optional[str], typer.Option(
        "--json",
        help="Save results to JSON file at specified path"
    )] = None,
    sort_by: Annotated[Optional[str], typer.Option(
        "--sort-by",
        help="Sort results by field (e.g. 'cited_by_count:desc', 'publication_year', "
             "'display_name:asc'). Multiple sorts: 'year:desc,cited_by_count:desc'"
    )] = None,
    sample: Annotated[Optional[int], typer.Option(
        "--sample",
        help="Get random sample of results (max 10,000). "
             "Use with --seed for reproducible results"
    )] = None,
    seed: Annotated[Optional[int], typer.Option(
        "--seed",
        help="Seed for random sampling (used with --sample)"
    )] = 0,
    select: Annotated[Optional[str], typer.Option(
        "--select",
        help="Select specific fields to return (comma-separated). "
             "Example: 'id,doi,title,display_name'. "
             "If not specified, returns all fields."
    )] = None,
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
      pyalex works --award-ids "AWARD123,AWARD456"
      pyalex works --search "AI" --abstract --json ai_works.json
      pyalex works --group-by "oa_status"
      pyalex works --group-by "publication_year" --search "COVID-19"
      pyalex works --sort-by "cited_by_count:desc" --limit 100
      pyalex works --sample 50 --seed 123
      pyalex works --search "climate change" \\
        --sort-by "publication_year:desc,cited_by_count:desc"
    """
    try:
        # Check for mutually exclusive options
        if all_results and limit is not None:
            typer.echo("Error: --all and --limit are mutually exclusive", err=True)
            raise typer.Exit(1)
        
        # Search works
        query = Works()
        
        if search:
            query = query.search(search)
        if author_ids:
            # Use the generalized helper for ID list handling
            query = add_id_list_option_to_command(
                query, author_ids, 'works_author', Works
            )
        if institution_ids:
            # Use the generalized helper for ID list handling
            query = add_id_list_option_to_command(
                query, institution_ids, 'works_institution', Works
            )
        
        if publication_year:
            # Handle publication year ranges (e.g., "2019:2020") or single years
            if ":" in publication_year:
                try:
                    start_year, end_year = publication_year.split(":")
                    start_year = int(start_year.strip())
                    end_year = int(end_year.strip())
                    
                    # For inclusive range, use >= start_year and <= end_year
                    # Since PyAlex only supports > and <, we'll use 
                    # (start_year - 1) and (end_year + 1)
                    query = query.filter_gt(publication_year=start_year - 1)
                    query = query.filter_lt(publication_year=end_year + 1)
                except ValueError:
                    typer.echo(
                        "Error: Invalid year range format. Use 'start:end' "
                        "(e.g., '2019:2020')", 
                        err=True
                    )
                    raise typer.Exit(1) from None
            else:
                try:
                    year = int(publication_year.strip())
                    query = query.filter(publication_year=year)
                except ValueError:
                    typer.echo(
                        "Error: Invalid year format. Use a single year or range "
                        "(e.g., '2020' or '2019:2020')", 
                        err=True
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
                    
                    # Validate date format (basic check for YYYY-MM-DD)
                    datetime.datetime.strptime(start_date, "%Y-%m-%d")
                    datetime.datetime.strptime(end_date, "%Y-%m-%d")
                    
                    # For inclusive range, we need >= start_date and <= end_date
                    # We'll use from_publication_date and to_publication_date
                    query = query.filter(from_publication_date=start_date)
                    query = query.filter(to_publication_date=end_date)
                except ValueError as ve:
                    typer.echo(
                        "Error: Invalid date range format. Use "
                        "'YYYY-MM-DD:YYYY-MM-DD' (e.g., '2019-01-01:2020-12-31')", 
                        err=True
                    )
                    raise typer.Exit(1) from ve
            else:
                try:
                    # Validate single date format
                    datetime.datetime.strptime(publication_date.strip(), "%Y-%m-%d")
                    query = query.filter(publication_date=publication_date.strip())
                except ValueError:
                    typer.echo(
                        "Error: Invalid date format. Use YYYY-MM-DD format "
                        "(e.g., '2020-01-01') or range '2019-01-01:2020-12-31'", 
                        err=True
                    )
                    raise typer.Exit(1) from None
        
        if work_type:
            query = query.filter(type=work_type)
        
        if topic_ids:
            # Use the generalized helper for ID list handling
            query = add_id_list_option_to_command(
                query, topic_ids, 'works_topic', Works
            )
        
        if subfield_ids:
            # Use the generalized helper for ID list handling
            query = add_id_list_option_to_command(
                query, subfield_ids, 'works_subfield', Works
            )
        
        if funder_ids:
            # Use the generalized helper for ID list handling
            query = add_id_list_option_to_command(
                query, funder_ids, 'works_funder', Works
            )
        
        if award_ids:
            # Use the generalized helper for ID list handling
            query = add_id_list_option_to_command(
                query, award_ids, 'works_award', Works
            )

        # Apply common options (sort, sample, select)
        query = _validate_and_apply_common_options(
            query, all_results, limit, sample, seed, sort_by, select
        )

        # Handle group_by parameter
        if group_by:
            query = query.group_by(group_by)
            
            # Print debug URL before making the request
            _print_debug_url(query)
            
            try:
                # For group-by operations, retrieve all groups by default
                results = query.get(limit=100000)  # High limit to get all groups
                _print_debug_results(results)
            except Exception as api_error:
                if _debug_mode:
                    from pyalex.logger import get_logger
                    logger = get_logger()
                    logger.debug(f"API call failed: {api_error}")
                raise
            
            # Output grouped results
            _output_grouped_results(results, json_path)
            return
        
        # Print debug URL before making the request
        _print_debug_url(query)
        
        try:
            # Check if we need to handle any large ID lists
            large_id_attrs = [attr for attr in dir(query) if attr.startswith('_large_')]
            
            if large_id_attrs:
                # Handle large ID list using the generalized system
                attr_name = large_id_attrs[0]  # Take the first one found
                large_id_list = getattr(query, attr_name)
                delattr(query, attr_name)
                
                # Extract the filter config key from the attribute name
                # e.g., '_large_works_funder_list' -> 'works_funder'
                filter_config_key = (attr_name.replace('_large_', '')
                                   .replace('_list', ''))
                
                results = _handle_large_id_list(
                    query,
                    large_id_list,
                    filter_config_key,
                    Works,
                    filter_config_key.split('_')[1] + " IDs",  # e.g., "funder IDs"
                    all_results,
                    limit,
                    json_path
                )
            else:
                # Normal single query execution
                if _dry_run_mode:
                    _print_dry_run_query(
                        "Works query",
                        url=query.url
                    )
                    return
                
                if all_results:
                    # Get all results using pagination with progress bar
                    results = _paginate_with_progress(query, "works")
                elif limit is not None:
                    # Use smart execution (async or sync based on conditions)
                    results = _execute_query_smart(
                        query, all_results=False, limit=limit
                    )
                else:
                    results = query.get()  # Default first page
            
            _print_debug_results(results)
        except Exception as api_error:
            if _debug_mode:
                from pyalex.logger import get_logger
                logger = get_logger()
                logger.debug(f"API call failed: {api_error}")
            raise
        
        # Check if results is None or empty
        if results is None:
            typer.echo("No results returned from API", err=True)
            return
        
        # Always convert abstracts for all works in results
        if results:
            results = [_add_abstract_to_work(work) for work in results]
        _output_results(results, json_path)
            
    except Exception as e:
        _handle_cli_exception(e)



@app.command()
def authors(
    search: Annotated[Optional[str], typer.Option(
        "--search", "-s",
        help="Search term for authors"
    )] = None,
    institution_ids: Annotated[Optional[str], typer.Option(
        "--institution-ids",
        help="Filter by institution OpenAlex ID(s). Use comma-separated values for "
             "OR logic (e.g., --institution-ids 'I123,I456,I789')"
    )] = None,
    group_by: Annotated[Optional[str], typer.Option(
        "--group-by",
        help="Group results by field (e.g. 'cited_by_count', 'has_orcid', "
             "'works_count')"
    )] = None,
    all_results: Annotated[bool, typer.Option(
        "--all",
        help="Retrieve all results (default: first page only)"
    )] = False,
    limit: Annotated[Optional[int], typer.Option(
        "--limit", "-l",
        help="Maximum number of results to return (mutually exclusive with --all)"
    )] = None,
    json_path: Annotated[Optional[str], typer.Option(
        "--json",
        help="Save results to JSON file at specified path"
    )] = None,
    sort_by: Annotated[Optional[str], typer.Option(
        "--sort-by",
        help="Sort results by field (e.g. 'cited_by_count:desc', 'works_count', "
             "'display_name:asc'). Multiple sorts: 'works_count:desc,"
             "cited_by_count:desc'"
    )] = None,
    sample: Annotated[Optional[int], typer.Option(
        "--sample",
        help="Get random sample of results (max 10,000). "
             "Use with --seed for reproducible results"
    )] = None,
    seed: Annotated[Optional[int], typer.Option(
        "--seed",
        help="Seed for random sampling (used with --sample)"
    )] = 0,
    select: Annotated[Optional[str], typer.Option(
        "--select",
        help="Select specific fields to return (comma-separated). "
             "Example: 'id,display_name,orcid'. "
             "If not specified, returns all fields."
    )] = None,
):
    """
    Search and retrieve authors from OpenAlex.
    
    Examples:
      pyalex authors --search "John Smith"
      pyalex authors --institution-ids "I1234567890" --all
      pyalex authors --institution-ids "I123,I456,I789" --limit 50
      pyalex authors --group-by "cited_by_count" --json results.json
      pyalex authors --group-by "has_orcid"
      pyalex authors --sort-by "cited_by_count:desc" --limit 100
      pyalex authors --sample 25 --seed 456
    """
    try:
        # Check for mutually exclusive options
        if all_results and limit is not None:
            typer.echo("Error: --all and --limit are mutually exclusive", err=True)
            raise typer.Exit(1)
        
        # Search authors
        query = Authors()
        
        if search:
            query = query.search(search)
        if institution_ids:
            # Use the generalized helper for ID list handling
            query = add_id_list_option_to_command(
                query, institution_ids, 'authors_institution', Authors
            )
        
        # Apply common options (sort, sample, select)
        query = _validate_and_apply_common_options(
            query, all_results, limit, sample, seed, sort_by, select
        )

        # Handle group_by parameter
        if group_by:
            query = query.group_by(group_by)
            _print_debug_url(query)
            
            # For group-by operations, retrieve all groups by default
            results = query.get(limit=100000)  # High limit to get all groups
            _print_debug_results(results)
            
            # Output grouped results
            _output_grouped_results(results, json_path)
            return
        
        _print_debug_url(query)
        
        try:
            # Check if we need to handle any large ID lists
            large_id_attrs = [attr for attr in dir(query) if attr.startswith('_large_')]
            
            if large_id_attrs:
                # Handle large ID list using the generalized system
                attr_name = large_id_attrs[0]  # Take the first one found
                large_id_list = getattr(query, attr_name)
                delattr(query, attr_name)
                
                # Extract the filter config key from the attribute name
                filter_config_key = (attr_name.replace('_large_', '')
                                   .replace('_list', ''))
                
                results = _handle_large_id_list(
                    query,
                    large_id_list,
                    filter_config_key,
                    Authors,
                    filter_config_key.split('_')[1] + " IDs",
                    all_results,
                    limit,
                    json_path
                )
            else:
                # Standard single query execution
                if _dry_run_mode:
                    _print_dry_run_query(
                        "Authors query",
                        url=query.url
                    )
                    return
                
                if all_results:
                    limit_to_use = None  # Get all results
                elif limit is not None:
                    limit_to_use = limit  # Use specified limit
                else:
                    limit_to_use = 25  # Default first page
                results = query.get(limit=limit_to_use)
            
            _print_debug_results(results)
            _output_results(results, json_path)
                
        except Exception as api_error:
            if _debug_mode:
                from pyalex.logger import get_logger
                logger = get_logger()
                logger.debug(f"API call failed: {api_error}")
            raise
            
    except Exception as e:
        _handle_cli_exception(e)


@app.command()
def topics(
    search: Annotated[Optional[str], typer.Option(
        "--search", "-s",
        help="Search term for topics"
    )] = None,
    domain_ids: Annotated[Optional[str], typer.Option(
        "--domain-ids",
        help="Filter by domain OpenAlex ID(s). Use comma-separated values for "
             "OR logic (e.g., --domain-ids 'D123,D456,D789')"
    )] = None,
    field_ids: Annotated[Optional[str], typer.Option(
        "--field-ids",
        help="Filter by field OpenAlex ID(s). Use comma-separated values for "
             "OR logic (e.g., --field-ids 'F123,F456,F789')"
    )] = None,
    subfield_ids: Annotated[Optional[str], typer.Option(
        "--subfield-ids",
        help="Filter by subfield OpenAlex ID(s). Use comma-separated values for "
             "OR logic (e.g., --subfield-ids 'SF123,SF456,SF789')"
    )] = None,
    all_results: Annotated[bool, typer.Option(
        "--all",
        help="Retrieve all results (default: first page only)"
    )] = False,
    limit: Annotated[Optional[int], typer.Option(
        "--limit", "-l",
        help="Maximum number of results to return (mutually exclusive with --all)"
    )] = None,
    json_path: Annotated[Optional[str], typer.Option(
        "--json",
        help="Save results to JSON file at specified path"
    )] = None,
    sort_by: Annotated[Optional[str], typer.Option(
        "--sort-by",
        help="Sort results by field (e.g. 'cited_by_count:desc', 'works_count', "
             "'display_name:asc')"
    )] = None,
    sample: Annotated[Optional[int], typer.Option(
        "--sample",
        help="Get random sample of results (max 10,000). "
             "Use with --seed for reproducible results"
    )] = None,
    seed: Annotated[Optional[int], typer.Option(
        "--seed",
        help="Seed for random sampling (used with --sample)"
    )] = 0,
    select: Annotated[Optional[str], typer.Option(
        "--select",
        help="Select specific fields to return (comma-separated). "
             "Example: 'id,display_name,domain'. "
             "If not specified, returns all fields."
    )] = None,
):
    """
    Search and retrieve topics from OpenAlex.
    
    Examples:
      pyalex topics --search "artificial intelligence"
      pyalex topics --domain-ids "D1234567890" --all
      pyalex topics --domain-ids "D123,D456,D789" --limit 50
      pyalex topics --field-ids "F1234567890" --json topics.json
      pyalex topics --field-ids "F123,F456" --all
      pyalex topics --subfield-ids "SF1234567890"
      pyalex topics --subfield-ids "SF123,SF456,SF789"
      pyalex topics --sort-by "works_count:desc" --limit 100
      pyalex topics --sample 20 --seed 789
    """
    try:
        # Check for mutually exclusive options
        if all_results and limit is not None:
            typer.echo("Error: --all and --limit are mutually exclusive", err=True)
            raise typer.Exit(1)
        
        # Search topics
        query = Topics()
        
        if search:
            query = query.search(search)
        if domain_ids:
            # Use the generalized helper for ID list handling
            query = add_id_list_option_to_command(
                query, domain_ids, 'topics_domain', Topics
            )
        if field_ids:
            # Use the generalized helper for ID list handling
            query = add_id_list_option_to_command(
                query, field_ids, 'topics_field', Topics
            )
        if subfield_ids:
            # Use the generalized helper for ID list handling
            query = add_id_list_option_to_command(
                query, subfield_ids, 'topics_subfield', Topics
            )
        
        # Apply common options (sort, sample, select)
        query = _validate_and_apply_common_options(
            query, all_results, limit, sample, seed, sort_by, select
        )
        
        _print_debug_url(query)
        
        if _dry_run_mode:
            _print_dry_run_query("Topics query", url=query.url)
            return
        
        results = _execute_query_with_options(query, all_results, limit, "topics")
        _print_debug_results(results)
        _output_results(results, json_path)
            
    except Exception as e:
        _handle_cli_exception(e)



@app.command()
def sources(
    search: Annotated[Optional[str], typer.Option(
        "--search", "-s",
        help="Search term for sources (journals/venues)"
    )] = None,
    group_by: Annotated[Optional[str], typer.Option(
        "--group-by",
        help="Group results by field (e.g. 'type', 'is_oa', 'publisher')"
    )] = None,
    all_results: Annotated[bool, typer.Option(
        "--all",
        help="Retrieve all results (default: first page only)"
    )] = False,
    limit: Annotated[Optional[int], typer.Option(
        "--limit", "-l",
        help="Maximum number of results to return (mutually exclusive with --all)"
    )] = None,
    json_path: Annotated[Optional[str], typer.Option(
        "--json",
        help="Save results to JSON file at specified path"
    )] = None,
    sort_by: Annotated[Optional[str], typer.Option(
        "--sort-by",
        help="Sort results by field (e.g. 'cited_by_count:desc', 'works_count', "
             "'display_name:asc')"
    )] = None,
    sample: Annotated[Optional[int], typer.Option(
        "--sample",
        help="Get random sample of results (max 10,000). "
             "Use with --seed for reproducible results"
    )] = None,
    seed: Annotated[Optional[int], typer.Option(
        "--seed",
        help="Seed for random sampling (used with --sample)"
    )] = 0,
    select: Annotated[Optional[str], typer.Option(
        "--select",
        help="Select specific fields to return (comma-separated). "
             "Example: 'id,display_name,type'. "
             "If not specified, returns all fields."
    )] = None,
):
    """
    Search and retrieve sources (journals/venues) from OpenAlex.
    
    Examples:
      pyalex sources --search "Nature"
      pyalex sources --all
      pyalex sources --limit 100
      pyalex sources --group-by "type"
      pyalex sources --group-by "is_oa" --search "machine learning" --json sources.json
      pyalex sources --sort-by "works_count:desc" --limit 50
      pyalex sources --sample 30 --seed 101
    """
    try:
        # Check for mutually exclusive options
        if all_results and limit is not None:
            typer.echo("Error: --all and --limit are mutually exclusive", err=True)
            raise typer.Exit(1)
        
        # Search sources
        query = Sources()
        
        if search:
            query = query.search(search)
        
        # Apply common options (sort, sample, select)
        query = _validate_and_apply_common_options(
            query, all_results, limit, sample, seed, sort_by, select
        )
        
        # Handle group_by parameter
        if group_by:
            query = query.group_by(group_by)
            _print_debug_url(query)
            
            if _dry_run_mode:
                _print_dry_run_query("Sources group-by query", url=query.url)
                return
            
            # For group-by operations, retrieve all groups by default
            results = query.get(limit=100000)
            _print_debug_results(results)
            
            # Output grouped results
            _output_grouped_results(results, json_path)
            return
        
        _print_debug_url(query)
        
        if _dry_run_mode:
            _print_dry_run_query("Sources query", url=query.url)
            return
        
        results = _execute_query_with_options(query, all_results, limit, "sources")
        _print_debug_results(results)
        _output_results(results, json_path)
            
    except Exception as e:
        _handle_cli_exception(e)


@app.command()
def institutions(
    search: Annotated[Optional[str], typer.Option(
        "--search", "-s",
        help="Search term for institutions"
    )] = None,
    country_code: Annotated[Optional[str], typer.Option(
        "--country",
        help="Filter by country code (e.g. US, UK, CA)"
    )] = None,
    group_by: Annotated[Optional[str], typer.Option(
        "--group-by",
        help="Group results by field (e.g. 'country_code', 'continent', "
             "'type', 'cited_by_count', 'works_count')"
    )] = None,
    all_results: Annotated[bool, typer.Option(
        "--all",
        help="Retrieve all results (default: first page only)"
    )] = False,
    limit: Annotated[Optional[int], typer.Option(
        "--limit", "-l",
        help="Maximum number of results to return (mutually exclusive with --all)"
    )] = None,
    json_path: Annotated[Optional[str], typer.Option(
        "--json",
        help="Save results to JSON file at specified path"
    )] = None,
    sort_by: Annotated[Optional[str], typer.Option(
        "--sort-by",
        help="Sort results by field (e.g. 'cited_by_count:desc', 'works_count', "
             "'display_name:asc')"
    )] = None,
    sample: Annotated[Optional[int], typer.Option(
        "--sample",
        help="Get random sample of results (max 10,000). "
             "Use with --seed for reproducible results"
    )] = None,
    seed: Annotated[Optional[int], typer.Option(
        "--seed",
        help="Seed for random sampling (used with --sample)"
    )] = 0,
    select: Annotated[Optional[str], typer.Option(
        "--select",
        help="Select specific fields to return (comma-separated). "
             "Example: 'id,display_name,country_code'. "
             "If not specified, returns all fields."
    )] = None,
):
    """
    Search and retrieve institutions from OpenAlex.
    
    Examples:
      pyalex institutions --search "Harvard"
      pyalex institutions --country US --all
      pyalex institutions --country US --limit 100
      pyalex institutions --group-by "country_code" --json institutions.json
      pyalex institutions --group-by "type"
      pyalex institutions --sort-by "works_count:desc" --limit 50
      pyalex institutions --sample 25 --seed 202
    """
    try:
        # Check for mutually exclusive options
        if all_results and limit is not None:
            typer.echo("Error: --all and --limit are mutually exclusive", err=True)
            raise typer.Exit(1)
        
        # Search institutions
        query = Institutions()
        
        if search:
            query = query.search(search)
        if country_code:
            query = query.filter(country_code=country_code)
        
        # Apply common options (sort, sample, select)
        query = _validate_and_apply_common_options(
            query, all_results, limit, sample, seed, sort_by, select
        )
        
        # Handle group_by parameter
        if group_by:
            query = query.group_by(group_by)
            _print_debug_url(query)
            
            if _dry_run_mode:
                _print_dry_run_query("Institutions group-by query", url=query.url)
                return
            
            # For group-by operations, retrieve all groups by default
            results = query.get(limit=100000)
            _print_debug_results(results)
            
            # Output grouped results
            _output_grouped_results(results, json_path)
            return
        
        _print_debug_url(query)
        
        if _dry_run_mode:
            _print_dry_run_query("Institutions query", url=query.url)
            return
        
        results = _execute_query_with_options(query, all_results, limit, "institutions")
        _print_debug_results(results)
        _output_results(results, json_path)
            
    except Exception as e:
        _handle_cli_exception(e)



@app.command()
def publishers(
    search: Annotated[Optional[str], typer.Option(
        "--search", "-s",
        help="Search term for publishers"
    )] = None,
    group_by: Annotated[Optional[str], typer.Option(
        "--group-by",
        help="Group results by field (e.g. 'country_code', 'hierarchy_level')"
    )] = None,
    all_results: Annotated[bool, typer.Option(
        "--all",
        help="Retrieve all results (default: first page only)"
    )] = False,
    limit: Annotated[Optional[int], typer.Option(
        "--limit", "-l",
        help="Maximum number of results to return (mutually exclusive with --all)"
    )] = None,
    json_path: Annotated[Optional[str], typer.Option(
        "--json",
        help="Save results to JSON file at specified path"
    )] = None,
    sort_by: Annotated[Optional[str], typer.Option(
        "--sort-by",
        help="Sort results by field (e.g. 'cited_by_count:desc', 'works_count', "
             "'display_name:asc')"
    )] = None,
    sample: Annotated[Optional[int], typer.Option(
        "--sample",
        help="Get random sample of results (max 10,000). "
             "Use with --seed for reproducible results"
    )] = None,
    seed: Annotated[Optional[int], typer.Option(
        "--seed",
        help="Seed for random sampling (used with --sample)"
    )] = 0,
    select: Annotated[Optional[str], typer.Option(
        "--select",
        help="Select specific fields to return (comma-separated). "
             "Example: 'id,display_name,country_code'. "
             "If not specified, returns all fields."
    )] = None,
):
    """
    Search and retrieve publishers from OpenAlex.
    
    Examples:
      pyalex publishers --search "Elsevier"
      pyalex publishers --all
      pyalex publishers --group-by "country_code" --json publishers.json
      pyalex publishers --sort-by "works_count:desc" --limit 50
      pyalex publishers --sample 15 --seed 303
    """
    try:
        # Check for mutually exclusive options
        if all_results and limit is not None:
            typer.echo("Error: --all and --limit are mutually exclusive", err=True)
            raise typer.Exit(1)
        
        # Search publishers
        query = Publishers()
        
        if search:
            query = query.search(search)
        
        # Apply common options (sort, sample, select)
        query = _validate_and_apply_common_options(
            query, all_results, limit, sample, seed, sort_by, select
        )
            
        # Handle group_by parameter
        if group_by:
            query = query.group_by(group_by)
            _print_debug_url(query)
            
            if _dry_run_mode:
                _print_dry_run_query("Publishers group-by query", url=query.url)
                return
            
            # For group-by operations, retrieve all groups by default
            results = query.get(limit=100000)
            _print_debug_results(results)
            
            # Output grouped results
            _output_grouped_results(results, json_path)
            return
        
        _print_debug_url(query)
        
        if _dry_run_mode:
            _print_dry_run_query("Publishers query", url=query.url)
            return
        
        results = _execute_query_with_options(query, all_results, limit, "publishers")
        _print_debug_results(results)
        _output_results(results, json_path)
            
    except Exception as e:
        _handle_cli_exception(e)


@app.command()
def funders(
    search: Annotated[Optional[str], typer.Option(
        "--search", "-s",
        help="Search term for funders"
    )] = None,
    country_code: Annotated[Optional[str], typer.Option(
        "--country",
        help="Filter by country code (e.g. US, UK, CA)"
    )] = None,
    group_by: Annotated[Optional[str], typer.Option(
        "--group-by",
        help="Group results by field (e.g. 'country_code', 'works_count')"
    )] = None,
    all_results: Annotated[bool, typer.Option(
        "--all",
        help="Retrieve all results (default: first page only)"
    )] = False,
    limit: Annotated[Optional[int], typer.Option(
        "--limit", "-l",
        help="Maximum number of results to return (mutually exclusive with --all)"
    )] = None,
    json_path: Annotated[Optional[str], typer.Option(
        "--json",
        help="Save results to JSON file at specified path"
    )] = None,
    sort_by: Annotated[Optional[str], typer.Option(
        "--sort-by",
        help="Sort results by field (e.g. 'cited_by_count:desc', 'works_count', "
             "'display_name:asc')"
    )] = None,
    sample: Annotated[Optional[int], typer.Option(
        "--sample",
        help="Get random sample of results (max 10,000). "
             "Use with --seed for reproducible results"
    )] = None,
    seed: Annotated[Optional[int], typer.Option(
        "--seed",
        help="Seed for random sampling (used with --sample)"
    )] = None,
):
    """
    Search and retrieve funders from OpenAlex.
    
    Examples:
      pyalex funders --search "NSF"
      pyalex funders --country US --all
      pyalex funders --group-by "country_code" --json funders.json
      pyalex funders --sort-by "works_count:desc" --limit 50
      pyalex funders --sample 10 --seed 404
    """
    try:
        # Check for mutually exclusive options
        if all_results and limit is not None:
            typer.echo("Error: --all and --limit are mutually exclusive", err=True)
            raise typer.Exit(1)
        
        # Search funders
        query = Funders()
        
        if search:
            query = query.search(search)
        if country_code:
            query = query.filter(country_code=country_code)
        
        # Apply common options (sort, sample)
        query = _validate_and_apply_common_options(
            query, all_results, limit, sample, seed, sort_by
        )
        
        # Handle group_by parameter
        if group_by:
            query = query.group_by(group_by)
            _print_debug_url(query)
            
            if _dry_run_mode:
                _print_dry_run_query("Funders group-by query", url=query.url)
                return
            
            # For group-by operations, retrieve all groups by default
            results = query.get(limit=100000)
            _print_debug_results(results)
            
            # Output grouped results
            _output_grouped_results(results, json_path)
            return
        
        _print_debug_url(query)
        
        if _dry_run_mode:
            _print_dry_run_query("Funders query", url=query.url)
            return
        
        results = _execute_query_with_options(query, all_results, limit, "funders")
        _print_debug_results(results)
        _output_results(results, json_path)
            
    except Exception as e:
        _handle_cli_exception(e)



@app.command()
def domains(
    search: Annotated[Optional[str], typer.Option(
        "--search", "-s",
        help="Search term for domains"
    )] = None,
    all_results: Annotated[bool, typer.Option(
        "--all",
        help="Retrieve all results (default: first page only)"
    )] = False,
    limit: Annotated[Optional[int], typer.Option(
        "--limit", "-l",
        help="Maximum number of results to return (mutually exclusive with --all)"
    )] = None,
    json_path: Annotated[Optional[str], typer.Option(
        "--json",
        help="Save results to JSON file at specified path"
    )] = None,
    sort_by: Annotated[Optional[str], typer.Option(
        "--sort-by",
        help="Sort results by field (e.g. 'cited_by_count:desc', 'works_count', "
             "'display_name:asc')"
    )] = None,
    sample: Annotated[Optional[int], typer.Option(
        "--sample",
        help="Get random sample of results (max 10,000). "
             "Use with --seed for reproducible results"
    )] = None,
    seed: Annotated[Optional[int], typer.Option(
        "--seed",
        help="Seed for random sampling (used with --sample)"
    )] = None,
):
    """
    Search and retrieve domains from OpenAlex.
    
    Examples:
      pyalex domains --search "Physical Sciences"
      pyalex domains --all --json domains.json
      pyalex domains --sort-by "works_count:desc" --limit 10
      pyalex domains --sample 3 --seed 505
    """
    try:
        # Check for mutually exclusive options
        if all_results and limit is not None:
            typer.echo("Error: --all and --limit are mutually exclusive", err=True)
            raise typer.Exit(1)
        
        # Search domains
        query = Domains()
        
        if search:
            query = query.search(search)
        
        # Apply common options (sort, sample)
        query = _validate_and_apply_common_options(
            query, all_results, limit, sample, seed, sort_by
        )
        
        _print_debug_url(query)
        
        if _dry_run_mode:
            _print_dry_run_query("Domains query", url=query.url)
            return
        
        results = _execute_query_with_options(query, all_results, limit, "domains")
        _print_debug_results(results)
        _output_results(results, json_path)
            
    except Exception as e:
        _handle_cli_exception(e)


@app.command()
def fields(
    search: Annotated[Optional[str], typer.Option(
        "--search", "-s",
        help="Search term for fields"
    )] = None,
    all_results: Annotated[bool, typer.Option(
        "--all",
        help="Retrieve all results (default: first page only)"
    )] = False,
    limit: Annotated[Optional[int], typer.Option(
        "--limit", "-l",
        help="Maximum number of results to return (mutually exclusive with --all)"
    )] = None,
    json_path: Annotated[Optional[str], typer.Option(
        "--json",
        help="Save results to JSON file at specified path"
    )] = None,
    sort_by: Annotated[Optional[str], typer.Option(
        "--sort-by",
        help="Sort results by field (e.g. 'cited_by_count:desc', 'works_count', "
             "'display_name:asc')"
    )] = None,
    sample: Annotated[Optional[int], typer.Option(
        "--sample",
        help="Get random sample of results (max 10,000). "
             "Use with --seed for reproducible results"
    )] = None,
    seed: Annotated[Optional[int], typer.Option(
        "--seed",
        help="Seed for random sampling (used with --sample)"
    )] = None,
):
    """
    Search and retrieve fields from OpenAlex.
    
    Examples:
      pyalex fields --search "Computer Science"
      pyalex fields --all
      pyalex fields --json fields.json
      pyalex fields --sort-by "works_count:desc" --limit 20
      pyalex fields --sample 5 --seed 606
    """
    try:
        # Check for mutually exclusive options
        if all_results and limit is not None:
            typer.echo("Error: --all and --limit are mutually exclusive", err=True)
            raise typer.Exit(1)
        
        # Search fields
        query = Fields()
        
        if search:
            query = query.search(search)
        
        # Apply common options (sort, sample)
        query = _validate_and_apply_common_options(
            query, all_results, limit, sample, seed, sort_by
        )
            
        _print_debug_url(query)
        
        if _dry_run_mode:
            _print_dry_run_query("Fields query", url=query.url)
            return
        
        results = _execute_query_with_options(query, all_results, limit, "fields")
        _print_debug_results(results)
        _output_results(results, json_path)
            
    except Exception as e:
        _handle_cli_exception(e)



@app.command()
def subfields(
    search: Annotated[Optional[str], typer.Option(
        "--search", "-s",
        help="Search term for subfields"
    )] = None,
    all_results: Annotated[bool, typer.Option(
        "--all",
        help="Retrieve all results (default: first page only)"
    )] = False,
    limit: Annotated[Optional[int], typer.Option(
        "--limit", "-l",
        help="Maximum number of results to return (mutually exclusive with --all)"
    )] = None,
    json_path: Annotated[Optional[str], typer.Option(
        "--json",
        help="Save results to JSON file at specified path"
    )] = None,
    sort_by: Annotated[Optional[str], typer.Option(
        "--sort-by",
        help="Sort results by field (e.g. 'cited_by_count:desc', 'works_count', "
             "'display_name:asc')"
    )] = None,
    sample: Annotated[Optional[int], typer.Option(
        "--sample",
        help="Get random sample of results (max 10,000). "
             "Use with --seed for reproducible results"
    )] = None,
    seed: Annotated[Optional[int], typer.Option(
        "--seed",
        help="Seed for random sampling (used with --sample)"
    )] = None,
):
    """
    Search and retrieve subfields from OpenAlex.
    
    Examples:
      pyalex subfields --search "Machine Learning"
      pyalex subfields --all
      pyalex subfields --json subfields.json
      pyalex subfields --sort-by "works_count:desc" --limit 30
      pyalex subfields --sample 8 --seed 707
    """
    try:
        # Check for mutually exclusive options
        if all_results and limit is not None:
            typer.echo("Error: --all and --limit are mutually exclusive", err=True)
            raise typer.Exit(1)
        
        # Search subfields
        query = Subfields()
        
        if search:
            query = query.search(search)
        
        # Apply common options (sort, sample)
        query = _validate_and_apply_common_options(
            query, all_results, limit, sample, seed, sort_by
        )
            
        _print_debug_url(query)
        
        if _dry_run_mode:
            _print_dry_run_query("Subfields query", url=query.url)
            return
        
        results = _execute_query_with_options(query, all_results, limit, "subfields")
        _print_debug_results(results)
        _output_results(results, json_path)
            
    except Exception as e:
        _handle_cli_exception(e)



@app.command()
def keywords(
    search: Annotated[Optional[str], typer.Option(
        "--search", "-s",
        help="Search term for keywords"
    )] = None,
    all_results: Annotated[bool, typer.Option(
        "--all",
        help="Retrieve all results (default: first page only)"
    )] = False,
    limit: Annotated[Optional[int], typer.Option(
        "--limit", "-l",
        help="Maximum number of results to return (mutually exclusive with --all)"
    )] = None,
    json_path: Annotated[Optional[str], typer.Option(
        "--json",
        help="Save results to JSON file at specified path"
    )] = None,
    sort_by: Annotated[Optional[str], typer.Option(
        "--sort-by",
        help="Sort results by field (e.g. 'cited_by_count:desc', 'works_count', "
             "'display_name:asc')"
    )] = None,
    sample: Annotated[Optional[int], typer.Option(
        "--sample",
        help="Get random sample of results (max 10,000). "
             "Use with --seed for reproducible results"
    )] = None,
    seed: Annotated[Optional[int], typer.Option(
        "--seed",
        help="Seed for random sampling (used with --sample)"
    )] = None,
    select: Annotated[Optional[str], typer.Option(
        "--select",
        help="Select specific fields to return (comma-separated). "
             "Example: 'id,display_name,score'. "
             "If not specified, returns all fields."
    )] = None,
):
    """
    Search and retrieve keywords from OpenAlex.
    
    Examples:
      pyalex keywords --search "artificial intelligence"
      pyalex keywords --all --json keywords.json
      pyalex keywords --sort-by "works_count:desc" --limit 25
      pyalex keywords --sample 12 --seed 808
    """
    try:
        # Check for mutually exclusive options
        if all_results and limit is not None:
            typer.echo("Error: --all and --limit are mutually exclusive", err=True)
            raise typer.Exit(1)
        
        # Search keywords
        query = Keywords()
        
        if search:
            query = query.search(search)
        
        # Apply common options (sort, sample, select)
        query = _validate_and_apply_common_options(
            query, all_results, limit, sample, seed, sort_by, select
        )
            
        _print_debug_url(query)
        
        if _dry_run_mode:
            _print_dry_run_query("Keywords query", url=query.url)
            return
        
        results = _execute_query_with_options(query, all_results, limit, "keywords")
        _print_debug_results(results)
        _output_results(results, json_path)
            
    except Exception as e:
        _handle_cli_exception(e)

            


@app.command()
def from_ids(
    json_path: Annotated[Optional[str], typer.Option(
        "--json",
        help="Save results to JSON file at specified path"
    )] = None,
):
    """
    Retrieve multiple entities by their OpenAlex IDs from stdin.
    
    This command automatically detects the entity type from the ID format and retrieves
    the appropriate entities. It can handle mixed entity types in the same input.
    Up to 100 IDs of the same type can be retrieved in a single query using OR logic.
    
    Supported ID formats:
    - W: Works
    - A: Authors  
    - I: Institutions
    - S: Sources (journals/venues)
    - T: Topics
    - P: Publishers
    - F: Funders
    - K: Keywords
    - 1-digit: Domains (e.g., "1", "2")
    - 2-digit: Fields (e.g., "10", "23") 
    - 4-digit: Subfields (e.g., "1234", "5678")
    
    Examples:
      echo '["W1234", "A5678", "I9012"]' | pyalex from-ids --json results.json
      echo -e "A1234567890\\nW9876543210" | pyalex from-ids
      echo '["1", "10", "1234"]' | pyalex from-ids  # Domain, Field, Subfield
    """
    try:
        # Read from stdin
        stdin_content = sys.stdin.read().strip()
        
        if not stdin_content:
            typer.echo("Error: No input provided via stdin", err=True)
            raise typer.Exit(1)
        
        # Try to parse as JSON array first
        entity_ids = []
        try:
            parsed = json.loads(stdin_content)
            if isinstance(parsed, list):
                entity_ids = parsed
            else:
                typer.echo(
                    "Error: JSON input must be an array of entity IDs",
                    err=True
                )
                raise typer.Exit(1)
        except json.JSONDecodeError:
            # If not valid JSON, treat as newline-separated IDs
            entity_ids = [
                line.strip() 
                for line in stdin_content.split('\n') 
                if line.strip()
            ]
        
        if not entity_ids:
            typer.echo("Error: No entity IDs found in input", err=True)
            raise typer.Exit(1)
        
        # Group IDs by entity type for batch processing
        entity_groups = {}
        
        def _detect_entity_type(entity_id):
            """Detect the entity type from the OpenAlex ID prefix."""
            # Clean up the ID (remove URL prefix if present)
            clean_id = entity_id.replace('https://openalex.org/', '').strip()
            clean_id = clean_id.strip('/')
            
            # Check for digit-only patterns first (domains, fields, subfields)
            if clean_id.isdigit():
                digit_count = len(clean_id)
                if digit_count == 1:
                    return Domains  # Single digit = domain
                elif digit_count == 2:
                    return Fields   # Two digits = field
                elif digit_count == 4:
                    return Subfields  # Four digits = subfield
            
            # Check for letter prefix patterns
            prefix_mapping = {
                'W': Works,
                'A': Authors,
                'I': Institutions,
                'S': Sources,
                'T': Topics,
                'P': Publishers,
                'F': Funders,
                'K': Keywords,  # Keywords sometimes use K prefix
            }
            
            # Check for single-letter prefixes
            if len(clean_id) > 1 and clean_id[0].upper() in prefix_mapping:
                # Verify it follows the pattern: letter + digits
                if clean_id[1:].isdigit():
                    prefix = clean_id[0].upper()
                    return prefix_mapping[prefix]
            
            # Raise error for unrecognized formats
            supported_formats = (list(prefix_mapping.keys()) + 
                                ['1-digit (Domains)', '2-digit (Fields)', 
                                 '4-digit (Subfields)'])
            raise ValueError(f"Unrecognized entity ID format: {entity_id}. "
                            f"Supported formats: {', '.join(supported_formats)}")
        
        # Group entity IDs by type
        for entity_id in entity_ids:
            try:
                entity_class = _detect_entity_type(entity_id)
                class_name = entity_class.__name__
                
                if class_name not in entity_groups:
                    entity_groups[class_name] = {'class': entity_class, 'ids': []}
                
                entity_groups[class_name]['ids'].append(entity_id)
                
            except ValueError as e:
                typer.echo(f"Warning: {e}", err=True)
                continue
        
        if not entity_groups:
            typer.echo("Error: No valid entity IDs found", err=True)
            raise typer.Exit(1)
        
        # Retrieve entities by type using async processing
        all_results = []
        
        for class_name, group_info in entity_groups.items():
            entity_class = group_info['class']
            ids = group_info['ids']
            
            if _debug_mode:
                typer.echo(
                    f"[DEBUG] Retrieving {len(ids)} {class_name.lower()}(s)", 
                    err=True
                )
            
            try:
                # Use async processing for batch retrieval
                import asyncio
                batch_results = asyncio.run(
                    _async_retrieve_entities(entity_class, ids, class_name)
                )
                
                if batch_results:
                    all_results.extend(batch_results)
                
            except Exception as e:
                _handle_cli_exception(e)
        
        if not all_results:
            typer.echo("No results retrieved", err=True)
            return
        
        # Output results
        _output_results(all_results, json_path)
        
    except Exception as e:
        _handle_cli_exception(e)


@app.command()
def show(
    file_path: Annotated[Optional[str], typer.Argument(
        help="Path to the JSON file to display (if not provided, reads from stdin)"
    )] = None,
    json_path: Annotated[Optional[str], typer.Option(
        "--json",
        help="Save results to JSON file at specified path"
    )] = None,
):
    """
    Display a JSON file containing OpenAlex data in table format.
    
    This command takes a JSON file saved from previous PyAlex queries
    and displays it in a human-readable format. If no file path is provided,
    it reads JSON data from stdin.
    
    Examples:
      pyalex show reviews.json
      pyalex show reviews.json --json reformatted.json  
      pyalex show cited_by_reviews.json
      cat reviews.json | pyalex show
      echo '{"display_name": "Test Work", "id": "W123"}' | pyalex show \\
        --json output.json
    """
    try:
        # Read from file or stdin
        if file_path:
            # Check if file exists
            if not os.path.exists(file_path):
                typer.echo(f"Error: File '{file_path}' not found.", err=True)
                raise typer.Exit(1)
            
            # Read and parse JSON file
            try:
                with open(file_path, encoding='utf-8') as f:
                    data = json.load(f)
            except json.JSONDecodeError as e:
                typer.echo(f"Error: Invalid JSON in file '{file_path}': {e}", err=True)
                raise typer.Exit(1) from e
            except Exception as e:
                typer.echo(f"Error reading file '{file_path}': {e}", err=True)
                raise typer.Exit(1) from e
        else:
            # Read from stdin
            try:
                stdin_content = sys.stdin.read().strip()
                
                if not stdin_content:
                    typer.echo("Error: No input provided via stdin", err=True)
                    raise typer.Exit(1)
                
                data = json.loads(stdin_content)
                
            except json.JSONDecodeError as e:
                typer.echo(f"Error: Invalid JSON input: {e}", err=True)
                raise typer.Exit(1) from e
        
        # Determine if data is a single entity or a list
        if isinstance(data, dict):
            # Single entity
            _output_results(data, json_path, single=True)
        elif isinstance(data, list):
            # List of entities
            _output_results(data, json_path)
        else:
            typer.echo("Error: Input must be a JSON object or array", err=True)
            raise typer.Exit(1)
            
    except Exception as e:
        _handle_cli_exception(e)


if __name__ == "__main__":
    app()
