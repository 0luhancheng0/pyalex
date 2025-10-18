"""
Batch processing utilities for PyAlex CLI.

This module contains configurations and classes for handling large ID lists 
that need to be processed in batches for better performance and API compliance.
"""

import asyncio
import copy
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed
from dataclasses import dataclass
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional
from typing import Set
from typing import Tuple

import httpx
import typer

from pyalex import config


@dataclass
class BatchConfig:
    """Global configuration for batch processing."""
    debug_mode: bool = False
    dry_run_mode: bool = False
    batch_size: int = config.cli_batch_size
    max_concurrent: int = config.max_concurrent or 5
    
    @classmethod
    def create_from_cli(
        cls, debug_mode: bool, dry_run_mode: bool, batch_size: int
    ) -> 'BatchConfig':
        """Create configuration from CLI parameters."""
        return cls(
            debug_mode=debug_mode,
            dry_run_mode=dry_run_mode,
            batch_size=batch_size
        )


class BatchFilterConfig:
    """Configuration for handling large ID lists that need to be batched."""
    
    def __init__(self, filter_path: str, id_field: str = "id", or_separator: str = "|"):
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
    
    def apply_single_filter(self, query, id_value: str):
        """Apply filter for a single ID."""
        filter_dict = self._build_filter_dict(id_value)
        return query.filter(**filter_dict)
    
    def apply_batch_filter(self, query, id_list: List[str]):
        """Apply filter for a batch of IDs using OR logic."""
        or_filter_value = self.or_separator.join(id_list)
        filter_dict = self._build_filter_dict(or_filter_value)
        return query.filter(**filter_dict)
    
    def _build_filter_dict(self, value: str) -> Dict[str, Any]:
        """Build nested filter dictionary from dot-separated path."""
        if not self.filter_path:
            # Flat field like cited_by, cites
            return {self.id_field: value}
        
        # Split path into parts (e.g., "grants.funder" -> ["grants", "funder"])
        path_parts = self.filter_path.split('.')
        
        # Build nested dict: {"grants": {"funder": value}} for path "grants.funder"
        result = {self.id_field: value}
        for part in reversed(path_parts):
            result = {part: result}
        
        return result
    
    def remove_from_params(self, params: Dict[str, Any]) -> None:
        """Remove this filter from query parameters to avoid conflicts."""
        if not params or 'filter' not in params:
            return
        
        if not self.filter_path:
            # Flat field
            if self.id_field in params.get('filter', {}):
                del params['filter'][self.id_field]
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


class BatchFilterRegistry:
    """Registry for batch filter configurations."""
    
    def __init__(self):
        self._configs: Dict[str, BatchFilterConfig] = {}
        self._setup_default_configs()
    
    def _setup_default_configs(self):
        """Setup default filter configurations."""
        # Works filters - using correct OpenAlex field names
        self._configs.update({
            'works_funder': BatchFilterConfig("grants", "funder"),
            'works_award': BatchFilterConfig("grants", "award_id"),
            'works_author': BatchFilterConfig("authorships.author", "id"),
            'works_institution': BatchFilterConfig("authorships.institutions", "id"),
            'works_source': BatchFilterConfig("primary_location.source", "id"),
            'works_topic': BatchFilterConfig("primary_topic", "id"),
            'works_topics': BatchFilterConfig("topics", "id"),
            'works_subfield': BatchFilterConfig("primary_topic.subfield", "id"),
            'works_cited_by': BatchFilterConfig("", "cited_by"),
            'works_cites': BatchFilterConfig("", "cites"),
            
            # Authors filters  
            'authors_institution': BatchFilterConfig("last_known_institutions", "id"),
            
            # Topics filters
            'topics_domain': BatchFilterConfig("domain", "id"),
            'topics_field': BatchFilterConfig("field", "id"),
            'topics_subfield': BatchFilterConfig("subfield", "id"),
            
            # For future extensions
            'works_referenced_works': BatchFilterConfig("", "referenced_works"),
            'authors_works': BatchFilterConfig("", "works"),
            'institutions_works': BatchFilterConfig("", "works"),
            'sources_works': BatchFilterConfig("", "works"),
        })
    
    def register(self, filter_key: str, filter_path: str, id_field: str = "id"):
        """Register a new batch filter configuration."""
        self._configs[filter_key] = BatchFilterConfig(filter_path, id_field)
    
    def get(self, filter_key: str) -> BatchFilterConfig:
        """Get a filter configuration by key."""
        if filter_key not in self._configs:
            raise ValueError(f"Unknown filter config: {filter_key}")
        return self._configs[filter_key]
    
    def exists(self, filter_key: str) -> bool:
        """Check if a filter configuration exists."""
        return filter_key in self._configs


class ResultMerger:
    """Handles merging of results from multiple batches."""
    
    @staticmethod
    def merge_grouped_results(
        batch_results_list: List[Tuple[Any, int]]
    ) -> List[Dict[str, Any]]:
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
    
    @staticmethod
    def merge_entity_results(
        batch_results_list: List[Tuple[Any, int]]
    ) -> List[Dict[str, Any]]:
        """
        Merge entity results from multiple batches, removing duplicates.
        
        Args:
            batch_results_list: List of tuples (batch_results, batch_index)
            
        Returns:
            List of unique entity results
        """
        combined_results = []
        seen_ids: Set[str] = set()
        
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
        
        return combined_results


class HttpxBatchExecutor:
    """Handles batch execution using httpx for HTTP requests."""
    
    def __init__(self, config: BatchConfig):
        self.config = config
        self._client: Optional[httpx.Client] = None
    
    def __enter__(self):
        if httpx is None:
            raise ImportError("httpx is required for batch processing")
        self._client = httpx.Client(timeout=30.0)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            self._client.close()
    
    def execute_concurrent_requests(self, urls: List[str]) -> List[Dict[str, Any]]:
        """Execute multiple URLs concurrently using httpx."""
        if not self._client:
            raise RuntimeError("HttpxBatchExecutor must be used as context manager")
        
        results = []
        
        # Use ThreadPoolExecutor for concurrent requests
        with ThreadPoolExecutor(max_workers=self.config.max_concurrent) as executor:
            # Submit all requests
            future_to_url = {
                executor.submit(self._fetch_url, url): url 
                for url in urls
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                except Exception as e:
                    if self.config.debug_mode:
                        from .utils import _debug_print
                        _debug_print(f"Error fetching {url}: {e}", "ERROR")
        
        return results
    
    def _fetch_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch a single URL and return parsed JSON."""
        try:
            response = self._client.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            if self.config.debug_mode:
                from .utils import _debug_print
                _debug_print(f"Request failed for {url}: {e}", "ERROR")
            return None


class BatchProcessor:
    """Main class for processing large ID lists in batches."""
    
    def __init__(self, config: BatchConfig):
        self.config = config
        self.filter_registry = BatchFilterRegistry()
        self.result_merger = ResultMerger()
    
    def process_id_list(
        self,
        query,
        id_list: List[str],
        filter_config_key: str,
        entity_class,
        entity_name: str,
        all_results: bool = False,
        limit: Optional[int] = None,
        json_path: Optional[str] = None
    ):
        """
        Process a large ID list in batches.
        
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
        filter_config = self.filter_registry.get(filter_config_key)
        
        def create_batch_query(batch_ids: List[str]):
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
        
        return self._execute_batched_queries(
            id_list,
            create_batch_query,
            entity_name,
            all_results,
            limit,
            json_path
        )
    
    def apply_id_list_filter(self, query, id_list: List[str], filter_config_key: str, entity_class):
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
        filter_config = self.filter_registry.get(filter_config_key)
        
        if len(id_list) == 1:
            # Single ID
            return filter_config.apply_single_filter(query, id_list[0])
        elif len(id_list) <= self.config.batch_size:
            # Small list - use OR logic in single query
            return filter_config.apply_batch_filter(query, id_list)
        else:
            # Large list - mark for batch processing
            setattr(query, f'_large_{filter_config_key}_list', id_list)
            return query
    
    def add_id_list_option_to_command(
        self,
        query,
        option_value: str,
        filter_config_key: str,
        entity_class
    ):
        """
        Helper method to easily add ID list handling to any command.
        
        Args:
            query: The query object
            option_value: The comma-separated string of IDs from the CLI option
            filter_config_key: The filter configuration key
            entity_class: The entity class for large list handling
        
        Returns:
            Modified query object
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
        return self.apply_id_list_filter(
            query, cleaned_id_list, filter_config_key, entity_class
        )
    
    def _execute_batched_queries(
        self,
        id_list: List[str], 
        create_query_func: Callable[[List[str]], Any],
        entity_name: str,
        all_results: bool = False,
        limit: Optional[int] = None,
        json_path: Optional[str] = None
    ):
        """
        Execute batched queries for large lists of IDs.
        
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
        # Enhanced debugging information
        if self.config.debug_mode:
            from .utils import _debug_print
            _debug_print("=== Batch Processing Configuration ===", "BATCH")
            _debug_print(
                f"Total entities to process: {len(id_list)} {entity_name}", 
                "BATCH"
            )
            _debug_print(f"Batch size: {self.config.batch_size}", "BATCH")
            num_batches = (
                len(id_list) + self.config.batch_size - 1
            ) // self.config.batch_size
            _debug_print(f"Number of batches: {num_batches}", "BATCH")
            _debug_print(
                f"Processing parameters: all_results={all_results}, limit={limit}", 
                "BATCH"
            )
            _debug_print("=== Starting Batch Execution ===", "BATCH")
        
        if self.config.dry_run_mode:
            from .utils import _print_dry_run_query
            estimated_queries = (
                (len(id_list) + self.config.batch_size - 1) 
                // self.config.batch_size
            )
            _print_dry_run_query(
                f"Batched query for {len(id_list)} {entity_name}",
                estimated_queries=estimated_queries
            )
            return None
        
        # Use concurrent processing
        return self._execute_concurrent_batches(
            id_list, create_query_func, entity_name, all_results, limit, json_path
        )
    
    def _execute_single_batch(
        self, 
        batch_ids: List[str], 
        batch_index: int, 
        create_query_func, 
        entity_name: str,
        all_results: bool,
        limit: Optional[int]
    ):
        """Execute a single batch and return results."""
        # Create query for this batch
        batch_query = create_query_func(batch_ids)
        
        if self.config.debug_mode:
            from .utils import _debug_print
            _debug_print(
                f"=== Batch {batch_index + 1} Execution Details ===", "BATCH"
            )
            _debug_print(f"Batch size: {len(batch_ids)} IDs", "BATCH")
            _debug_print(f"Entity type: {entity_name}", "BATCH")
            _debug_print(f"API URL: {batch_query.url}", "BATCH")
            _debug_print(
                f"Execution mode: all_results={all_results}, limit={limit}", 
                "BATCH"
            )
        
        # Execute the batch query (using async pagination)
        try:
            if all_results:
                # Get all results for this batch using pagination
                if self.config.debug_mode:
                    from .utils import _debug_print
                    _debug_print(
                        f"Starting pagination for batch {batch_index + 1} "
                        f"({len(batch_ids)} {entity_name})", 
                        "BATCH"
                    )
                
                # Set a flag to indicate we're in batch context to prevent 
                # nested progress
                import threading
                batch_context = getattr(
                    threading.current_thread(), '_pyalex_batch_context', False
                )
                threading.current_thread()._pyalex_batch_context = True
                
                try:
                    from .utils import _paginate_with_progress
                    batch_name = f"{entity_name} (batch {batch_index + 1})"
                    batch_results = _paginate_with_progress(batch_query, batch_name)
                finally:
                    # Restore previous context
                    threading.current_thread()._pyalex_batch_context = batch_context
                
                if self.config.debug_mode:
                    from .utils import _debug_print
                    batch_result_count = len(batch_results) if batch_results else 0
                    _debug_print(
                        f"Pagination completed for batch {batch_index + 1}: "
                        f"{batch_result_count} results retrieved", 
                        "BATCH"
                    )
            elif limit is not None:
                if self.config.debug_mode:
                    from .utils import _debug_print
                    _debug_print(
                        f"Executing limited query for batch {batch_index + 1} "
                        f"with limit={limit}", "BATCH"
                    )
                batch_results = asyncio.run(batch_query.get(limit=limit))
                if self.config.debug_mode:
                    batch_result_count = len(batch_results) if batch_results else 0
                    _debug_print(
                        f"Limited query completed: {batch_result_count} results", 
                        "BATCH"
                    )
            else:
                if self.config.debug_mode:
                    from .utils import _debug_print
                    _debug_print(
                        f"Executing default query for batch {batch_index + 1} "
                        "(first page only)", "BATCH"
                    )
                batch_results = asyncio.run(batch_query.get())  # Default first page
                if self.config.debug_mode:
                    batch_result_count = len(batch_results) if batch_results else 0
                    _debug_print(
                        f"Default query completed: {batch_result_count} results", 
                        "BATCH"
                    )
                    
        except Exception as e:
            from .utils import _debug_print
            _debug_print(f"=== ERROR in Batch {batch_index + 1} ===", "ERROR")
            _debug_print(f"Entity type: {entity_name}", "ERROR")
            _debug_print(f"Batch size: {len(batch_ids)} IDs", "ERROR")
            _debug_print(f"Error message: {str(e)}", "ERROR")
            _debug_print(f"Error type: {type(e).__name__}", "ERROR")
            if self.config.debug_mode:
                import traceback
                _debug_print(f"Full traceback:\n{traceback.format_exc()}", "ERROR")
            raise
        
        batch_count = len(batch_results) if batch_results else 0
        if self.config.debug_mode:
            from .utils import _debug_print
            _debug_print(
                f"=== Batch {batch_index + 1} Summary ===", "BATCH"
            )
            _debug_print(f"Results returned: {batch_count}", "BATCH")
            _debug_print("Batch processing complete", "BATCH")
        
        return batch_results

    def _execute_concurrent_batches(
        self,
        id_list: List[str],
        create_query_func: Callable[[List[str]], Any],
        entity_name: str,
        all_results: bool = False,
        limit: Optional[int] = None,
        json_path: Optional[str] = None
    ):
        """Execute batches concurrently using standard library."""
        from .utils import _add_abstract_to_work
        
        num_batches = (
            (len(id_list) + self.config.batch_size - 1) 
            // self.config.batch_size
        )
        
        if not json_path:
            typer.echo(
                f"Processing {len(id_list)} {entity_name} "
                f"in {num_batches} batches...", 
                err=True
            )
            if num_batches > 10:
                typer.echo(
                    f"Note: Large number of batches ({num_batches}) "
                    f"may take several minutes",
                    err=True
                )
        
        # Check if this is a grouped query by examining a test query
        has_group_by = False
        if id_list:
            test_query = create_query_func([])  # Create empty query to check params
            has_group_by = (hasattr(test_query, 'params') and test_query.params and 
                           'group-by' in test_query.params)
        
        batch_results_list = []
        
        # Import rich progress here to avoid issues if rich is not available
        try:
            from rich.progress import BarColumn
            from rich.progress import Progress
            from rich.progress import SpinnerColumn
            from rich.progress import TextColumn
            from rich.progress import TimeElapsedColumn
            rich_available = True
        except ImportError:
            rich_available = False
        
        # Use rich progress bar if available and not in debug mode
        if rich_available and not self.config.debug_mode:
            # Create simple progress display with just batch-level progress
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TextColumn("({task.completed}/{task.total})"),
                TimeElapsedColumn(),
                expand=True
            ) as progress:
                # Single progress bar across batches
                batch_task_id = progress.add_task(
                    f"Processing {entity_name} batches", 
                    total=num_batches
                )
                
                # Process in batches with simple progress
                for i in range(0, len(id_list), self.config.batch_size):
                    batch_ids = id_list[i:i + self.config.batch_size]
                    batch_index = i // self.config.batch_size
                    
                    # Update progress description for current batch
                    batch_desc = (
                        f"Processing batch {batch_index + 1}/{num_batches}: "
                        f"{len(batch_ids)} {entity_name}"
                    )
                    progress.update(batch_task_id, description=batch_desc)
                    
                    batch_results = self._execute_single_batch(
                        batch_ids, batch_index, create_query_func, entity_name,
                        all_results, limit
                    )
                    
                    if batch_results:
                        batch_results_list.append((batch_results, batch_index))
                    
                    # Update progress after batch completion
                    progress.update(batch_task_id, advance=1)
        else:
            # Fallback to simple text progress or debug mode
            for i in range(0, len(id_list), self.config.batch_size):
                batch_ids = id_list[i:i + self.config.batch_size]
                batch_index = i // self.config.batch_size
                
                if self.config.debug_mode:
                    from .utils import _debug_print
                    _debug_print(
                        f"Processing batch {batch_index + 1}: "
                        f"{len(batch_ids)} {entity_name}",
                        "BATCH"
                    )
                else:
                    # Non-debug mode: show progress for large batch operations
                    if num_batches > 5:
                        typer.echo(
                            f"Processing batch {batch_index + 1}/{num_batches}...",
                            err=True
                        )
                
                batch_results = self._execute_single_batch(
                    batch_ids, batch_index, create_query_func, entity_name,
                    all_results, limit
                )
                
                if batch_results:
                    batch_results_list.append((batch_results, batch_index))
        
        # Merge results after all batches are processed
        if has_group_by:
            combined_results = self.result_merger.merge_grouped_results(
                batch_results_list
            )
        else:
            combined_results = self.result_merger.merge_entity_results(
                batch_results_list
            )
        
        # Convert abstracts for works if needed
        if 'works' in entity_name.lower():
            combined_results = [
                _add_abstract_to_work(work) for work in combined_results
            ]
        
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
                f"{len(id_list)} {entity_name}", 
                err=True
            )
        
        return results


# Global instances for backward compatibility
_global_config = BatchConfig()
_global_processor = BatchProcessor(_global_config)


def set_global_state(debug_mode: bool, dry_run_mode: bool, batch_size: int):
    """Set global state from main CLI configuration (backward compatibility)."""
    global _global_config, _global_processor
    _global_config = BatchConfig.create_from_cli(debug_mode, dry_run_mode, batch_size)
    _global_processor = BatchProcessor(_global_config)


def register_batch_filter(filter_key: str, filter_path: str, id_field: str = "id"):
    """Register a new batch filter configuration (backward compatibility)."""
    _global_processor.filter_registry.register(filter_key, filter_path, id_field)


def add_id_list_option_to_command(
    query, option_value: str, filter_config_key: str, entity_class
):
    """Helper function to easily add ID list handling to any command 
    (backward compatibility)."""
    return _global_processor.add_id_list_option_to_command(
        query, option_value, filter_config_key, entity_class
    )


def _handle_large_id_list(
    query, 
    id_list: List[str], 
    filter_config_key: str, 
    entity_class,
    entity_name: str,
    all_results: bool = False,
    limit: Optional[int] = None,
    json_path: Optional[str] = None
):
    """Generic handler for large ID lists (backward compatibility)."""
    return _global_processor.process_id_list(
        query, id_list, filter_config_key, entity_class, entity_name,
        all_results, limit, json_path
    )


# Legacy compatibility - these can be removed once callers are updated
BATCH_FILTER_CONFIGS = _global_processor.filter_registry._configs

def _merge_grouped_results(batch_results_list):
    """Legacy function for backward compatibility."""
    return ResultMerger.merge_grouped_results(batch_results_list)
