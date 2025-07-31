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

from pyalex import config, invert_abstract
from pyalex.core.config import MAX_PER_PAGE

# Global state - will be set by main CLI
_debug_mode = False
_dry_run_mode = False  
_batch_size = config.cli_batch_size

MAX_WIDTH = config.cli_max_width


def set_global_state(debug_mode: bool, dry_run_mode: bool, batch_size: int):
    """Set global state from main CLI configuration."""
    global _debug_mode, _dry_run_mode, _batch_size
    _debug_mode = debug_mode
    _dry_run_mode = dry_run_mode
    _batch_size = batch_size


def parse_range_filter(value: str):
    """
    Parse range or single value for filtering.
    
    Supports formats:
    - "100" -> exact value 100
    - "100:1000" -> range from 100 to 1000
    - ":1000" -> less than or equal to 1000  
    - "100:" -> greater than or equal to 100
    
    Returns:
        str: Formatted filter value for OpenAlex API
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
            # Range: start:end
            return f"{start}:{end}"
        elif start:
            # Greater than or equal: start:
            return f">{start}"
        elif end:
            # Less than or equal: :end
            return f"<{end}"
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
