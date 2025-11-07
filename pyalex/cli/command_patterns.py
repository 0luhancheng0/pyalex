"""
Common patterns and utilities for entity commands.

This module provides reusable patterns for CLI commands to reduce code duplication.
"""

import asyncio
from collections.abc import Callable
from functools import wraps
from typing import Any

import typer

from .formatting import print_debug
from .formatting import print_debug_results
from .formatting import print_debug_url
from .formatting import print_dry_run_query
from .formatting import print_error
from .state import is_debug
from .state import is_dry_run

# ============================================================================
# Practical Helper Functions for CLI Commands
# ============================================================================


def validate_json_output_options(json_flag: bool, json_path: str | None) -> str | None:
    """Validate and resolve JSON output options.

    Parameters
    ----------
    json_flag : bool
        Whether --json flag was provided
    json_path : Optional[str]
        Path provided via --json-file option

    Returns
    -------
    Optional[str]
        Effective JSON path: "-" for stdout, path string for file, or None

    Raises
    ------
    typer.Exit
        If both json_flag and json_path are provided (mutually exclusive)
    """
    if json_flag and json_path:
        typer.echo("Error: --json and --json-file are mutually exclusive", err=True)
        raise typer.Exit(1)
    elif json_flag:
        return "-"  # stdout
    elif json_path:
        return json_path
    return None


def validate_output_format_options(
    json_flag: bool, json_path: str | None, parquet_path: str | None
) -> tuple[str | None, str | None]:
    """Validate and resolve output format options.

    Parameters
    ----------
    json_flag : bool
        Whether --json flag was provided
    json_path : Optional[str]
        Path provided via --json-file option
    parquet_path : Optional[str]
        Path provided via --parquet-file option

    Returns
    -------
    tuple[Optional[str], Optional[str]]
        Tuple of (effective_json_path, parquet_path)
        - effective_json_path: "-" for stdout, path string for file, or None
        - parquet_path: path string for file or None

    Raises
    ------
    typer.Exit
        If multiple output format options are provided (mutually exclusive)
    """
    # Count how many output options are provided
    options_provided = sum([json_flag, json_path is not None, parquet_path is not None])

    if options_provided > 1:
        typer.echo(
            "Error: --json, --json-file, and --parquet-file are mutually exclusive",
            err=True,
        )
        raise typer.Exit(1)

    # Resolve JSON path
    if json_flag:
        effective_json_path = "-"  # stdout
    elif json_path:
        effective_json_path = json_path
    else:
        effective_json_path = None

    return effective_json_path, parquet_path


def validate_pagination_options(all_results: bool, limit: int | None) -> None:
    """Validate pagination options are not mutually exclusive.

    Parameters
    ----------
    all_results : bool
        Whether --all flag was provided
    limit : Optional[int]
        Limit value from --limit option

    Raises
    ------
    typer.Exit
        If both all_results and limit are provided (mutually exclusive)
    """
    if all_results and limit is not None:
        typer.echo("Error: --all and --limit are mutually exclusive", err=True)
        raise typer.Exit(1)


def execute_standard_query(
    query,
    entity_name: str,
    all_results: bool = False,
    limit: int | None = None,
    group_by: str | None = None,
):
    """Execute a standard entity query with debug/dry-run support.

    Handles the common pattern of:
    - Printing debug URL
    - Dry-run mode
    - Group-by special case (max 200 results, single page)
    - Pagination (all/limit/single page)
    - Debug results printing

    Parameters
    ----------
    query : BaseOpenAlex
        Query object to execute
    entity_name : str
        Name of entity for display (e.g., "works", "authors")
    all_results : bool, optional
        Whether to fetch all results with pagination
    limit : Optional[int], optional
        Maximum number of results to fetch
    group_by : Optional[str], optional
        Field to group by (if provided, uses different execution path)

    Returns
    -------
    results
        Query results (DataFrame, list, or grouped results)
    """
    from .utils import _dry_run_mode
    from .utils import _execute_query_smart
    from .utils import _paginate_with_progress
    from .utils import _print_debug_results
    from .utils import _print_debug_url
    from .utils import _print_dry_run_query

    # Print debug URL before execution
    _print_debug_url(query)

    # Handle dry-run mode
    if _dry_run_mode:
        _print_dry_run_query(f"{entity_name.capitalize()} query", url=query.url)
        return None

    # Handle group-by (special case: max 200 results, single page)
    if group_by:
        results = asyncio.run(query.get(per_page=200))
        _print_debug_results(results)
        return results

    # Handle normal query execution based on pagination options
    if all_results:
        results = _paginate_with_progress(query, entity_name)
    elif limit is not None:
        results = _execute_query_smart(query, all_results=False, limit=limit)
    else:
        results = asyncio.run(query.get())  # Default: first page only

    _print_debug_results(results)
    return results


def handle_large_id_list_if_needed(
    query,
    entity_class,
    all_results: bool,
    limit: int | None,
    json_path: str | None,
    group_by: str | None = None,
    selected_fields: list[str] | None = None,
):
    """Check for and handle large ID lists attached to query.

    Large ID lists are detected by checking for attributes starting with '_large_'
    on the query object. If found, delegates to batch processing.

    Parameters
    ----------
    query : BaseOpenAlex
        Query object to check
    entity_class : type
        Entity class (Works, Authors, etc.)
    all_results : bool
        Whether to fetch all results
    limit : Optional[int]
        Maximum number of results
    json_path : Optional[str]
        Path for JSON output (or "-" for stdout)
    group_by : Optional[str], optional
        Field to group by (if any)

    Returns
    -------
    Optional[results]
        Results if large ID list was handled, None otherwise.
        If not None, caller should return immediately (results already output).
    """
    from .batch import _handle_large_id_list
    from .utils import _add_abstract_to_work
    from .utils import _output_grouped_results
    from .utils import _output_results

    # Check for large ID list attributes
    large_id_attrs = [attr for attr in dir(query) if attr.startswith("_large_")]

    if not large_id_attrs:
        return None  # No large ID list, continue with normal query

    # Handle large ID list using batch processing
    attr_name = large_id_attrs[0]  # Take the first one found
    large_id_list = getattr(query, attr_name)
    delattr(query, attr_name)

    # Extract filter config key from attribute name
    # e.g., '_large_works_funder_list' -> 'works_funder'
    filter_config_key = attr_name.replace("_large_", "").replace("_list", "")

    # Execute batch processing
    results = _handle_large_id_list(
        query,
        large_id_list,
        filter_config_key,
        entity_class,
        filter_config_key.split("_")[1] + " IDs",  # e.g., "funder IDs"
        all_results,
        limit,
        json_path=json_path,
    )

    # Check if results is None or empty
    if results is None:
        typer.echo("No results returned from API", err=True)
        return results

    # Output results based on type
    if group_by:
        _output_grouped_results(results, json_path)
    else:
        # Convert DataFrame to list of dicts for processing
        import pandas as pd

        if isinstance(results, pd.DataFrame):
            results_list = results.to_dict("records")
        elif hasattr(results, "to_dict") and callable(results.to_dict):
            results_list = results.to_dict("records")
        elif isinstance(results, list):
            results_list = results
        else:
            results_list = list(results) if results is not None else []

        # Add abstracts for works (entity-specific processing)
        if entity_class.__name__ == "Works" and len(results_list) > 0:
            results_list = [_add_abstract_to_work(work) for work in results_list]

        _output_results(
            results_list,
            json_path,
            selected_fields=selected_fields,
        )

    return results  # Return results to signal they were handled


class CommandContext:
    """
    Context object passed to command handlers.

    Contains all common parameters and state.
    """

    def __init__(
        self,
        search: str | None = None,
        all_results: bool = False,
        limit: int | None = None,
        json_flag: bool = False,
        json_path: str | None = None,
        sort_by: str | None = None,
        group_by: str | None = None,
        **filters,
    ):
        self.search = search
        self.all_results = all_results
        self.limit = limit
        self.json_flag = json_flag
        self.json_path = json_path
        self.sort_by = sort_by
        self.group_by = group_by
        self.filters = filters

    def has_search(self) -> bool:
        """Check if search term is provided."""
        return self.search is not None

    def has_filters(self) -> bool:
        """Check if any filters are provided."""
        return any(v is not None for v in self.filters.values())

    def has_grouping(self) -> bool:
        """Check if grouping is requested."""
        return self.group_by is not None

    def should_output_json(self) -> bool:
        """Check if JSON output is requested."""
        return self.json_flag or self.json_path is not None


def apply_common_filters(query: Any, ctx: CommandContext) -> Any:
    """
    Apply common filters to a query based on context.

    Args:
        query: The query object to filter
        ctx: Command context with filter values

    Returns:
        Filtered query
    """
    # Apply search if provided
    if ctx.has_search():
        query = query.search(ctx.search)

    # Apply filters
    for filter_name, filter_value in ctx.filters.items():
        if filter_value is not None:
            # Handle special filter formats
            if isinstance(filter_value, str) and "," in filter_value:
                # Multiple values = OR logic
                query = query.filter(**{filter_name: filter_value})
            else:
                query = query.filter(**{filter_name: filter_value})

    # Apply sorting if provided
    if ctx.sort_by:
        query = query.sort(ctx.sort_by)

    return query


def handle_query_execution(
    query: Any, ctx: CommandContext, entity_name: str = "results"
) -> list[dict]:
    """
    Execute a query with progress tracking and error handling.

    Args:
        query: Query to execute
        ctx: Command context
        entity_name: Name of entity for progress display

    Returns:
        List of result dictionaries
    """
    from .utils import _execute_query_with_progress

    if is_debug():
        print_debug_url(query)

    if is_dry_run():
        print_dry_run_query(
            f"Would fetch {entity_name}",
            url=str(query.url) if hasattr(query, "url") else None,
        )
        return []

    try:
        results = _execute_query_with_progress(
            query, all_results=ctx.all_results, limit=ctx.limit, entity_name=entity_name
        )

        if is_debug():
            print_debug_results(results)

        return results
    except Exception as e:
        from .utils import _handle_cli_exception

        _handle_cli_exception(e)
        return []


def handle_output(
    results: list[dict], ctx: CommandContext, output_formatter: Callable | None = None
) -> None:
    """
    Handle output of results based on context.

    Args:
        results: Results to output
        ctx: Command context
        output_formatter: Optional custom formatter function
    """
    from .utils import _output_grouped_results
    from .utils import _output_results

    if ctx.has_grouping():
        _output_grouped_results(results, ctx.group_by, ctx.json_flag, ctx.json_path)
    else:
        if output_formatter:
            output_formatter(results, ctx.json_flag, ctx.json_path)
        else:
            _output_results(results, ctx.json_flag, ctx.json_path)


def create_entity_command_handler(
    entity_class: type,
    entity_name: str,
    custom_filters: Callable | None = None,
    custom_output: Callable | None = None,
) -> Callable:
    """
    Create a command handler for an entity type.

    This factory function creates a standardized command handler that:
    1. Creates a query from the entity class
    2. Applies filters from the context
    3. Executes the query with progress tracking
    4. Outputs results in the requested format

    Args:
        entity_class: The entity class (Works, Authors, etc.)
        entity_name: Name of entity for display
        custom_filters: Optional function to apply custom filters
        custom_output: Optional function for custom output formatting

    Returns:
        Command handler function
    """

    def handler(ctx: CommandContext) -> None:
        """Execute the command with the given context."""
        # Create base query
        query = entity_class()

        # Apply common filters
        query = apply_common_filters(query, ctx)

        # Apply custom filters if provided
        if custom_filters:
            query = custom_filters(query, ctx)

        # Execute query
        results = handle_query_execution(query, ctx, entity_name)

        # Output results
        if results is not None and len(results) > 0:
            handle_output(results, ctx, custom_output)

    return handler


def with_error_handling(func: Callable) -> Callable:
    """
    Decorator to add error handling to command functions.

    Args:
        func: Function to wrap

    Returns:
        Wrapped function with error handling
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            from .utils import _handle_cli_exception

            _handle_cli_exception(e)
            raise typer.Exit(1) from None

    return wrapper


def with_debug_output(func: Callable) -> Callable:
    """
    Decorator to add debug output to command functions.

    Args:
        func: Function to wrap

    Returns:
        Wrapped function with debug output
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        if is_debug():
            print_debug(f"Executing command: {func.__name__}")
        result = func(*args, **kwargs)
        if is_debug():
            print_debug(f"Command completed: {func.__name__}")
        return result

    return wrapper


def validate_mutually_exclusive(*param_names: str):
    """
    Create a validator for mutually exclusive parameters.

    Args:
        param_names: Names of parameters that are mutually exclusive

    Returns:
        Validator function
    """

    def validator(ctx: CommandContext) -> bool:
        """Check if parameters are mutually exclusive."""
        provided = [
            name for name in param_names if getattr(ctx, name, None) is not None
        ]

        if len(provided) > 1:
            print_error(
                f"Options {', '.join('--' + p.replace('_', '-') for p in provided)} "
                f"are mutually exclusive"
            )
            return False
        return True

    return validator


class BaseCommandBuilder:
    """
    Builder for creating standardized entity commands.

    Reduces boilerplate when creating new entity commands.
    """

    def __init__(self, entity_class: type, entity_name: str):
        """
        Initialize the builder.

        Args:
            entity_class: Entity class (Works, Authors, etc.)
            entity_name: Display name for the entity
        """
        self.entity_class = entity_class
        self.entity_name = entity_name
        self.custom_filters = None
        self.custom_output = None
        self.validators = []

    def with_custom_filters(self, filter_func: Callable):
        """Add custom filter function."""
        self.custom_filters = filter_func
        return self

    def with_custom_output(self, output_func: Callable):
        """Add custom output function."""
        self.custom_output = output_func
        return self

    def with_validator(self, validator: Callable):
        """Add a validator function."""
        self.validators.append(validator)
        return self

    def build(self) -> Callable:
        """
        Build the command handler.

        Returns:
            Command handler function
        """
        handler = create_entity_command_handler(
            self.entity_class, self.entity_name, self.custom_filters, self.custom_output
        )

        # Wrap with validators
        if self.validators:
            original_handler = handler

            def validated_handler(ctx: CommandContext) -> None:
                for validator in self.validators:
                    if not validator(ctx):
                        raise typer.Exit(1)
                return original_handler(ctx)

            handler = validated_handler

        # Add decorators
        handler = with_error_handling(handler)
        handler = with_debug_output(handler)

        return handler
