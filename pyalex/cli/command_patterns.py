"""
Common patterns and utilities for entity commands.

This module provides reusable patterns for CLI commands to reduce code duplication.
"""

from typing import Any, Callable, Dict, Optional, List
from functools import wraps
import typer

from .state import is_debug, is_dry_run
from .formatting import (
    print_debug, print_debug_url, print_debug_results, 
    print_dry_run_query, print_error
)


class CommandContext:
    """
    Context object passed to command handlers.
    
    Contains all common parameters and state.
    """
    
    def __init__(
        self,
        search: Optional[str] = None,
        all_results: bool = False,
        limit: Optional[int] = None,
        json_flag: bool = False,
        json_path: Optional[str] = None,
        sort_by: Optional[str] = None,
        group_by: Optional[str] = None,
        **filters
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
            if isinstance(filter_value, str) and ',' in filter_value:
                # Multiple values = OR logic
                query = query.filter(**{filter_name: filter_value})
            else:
                query = query.filter(**{filter_name: filter_value})
    
    # Apply sorting if provided
    if ctx.sort_by:
        query = query.sort(ctx.sort_by)
    
    return query


def handle_query_execution(
    query: Any,
    ctx: CommandContext,
    entity_name: str = "results"
) -> List[Dict]:
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
            url=str(query.url) if hasattr(query, 'url') else None
        )
        return []
    
    try:
        results = _execute_query_with_progress(
            query,
            all_results=ctx.all_results,
            limit=ctx.limit,
            entity_name=entity_name
        )
        
        if is_debug():
            print_debug_results(results)
        
        return results
    except Exception as e:
        from .utils import _handle_cli_exception
        _handle_cli_exception(e)
        return []


def handle_output(results: List[Dict], ctx: CommandContext, 
                  output_formatter: Optional[Callable] = None) -> None:
    """
    Handle output of results based on context.
    
    Args:
        results: Results to output
        ctx: Command context
        output_formatter: Optional custom formatter function
    """
    from .utils import _output_results, _output_grouped_results
    
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
    custom_filters: Optional[Callable] = None,
    custom_output: Optional[Callable] = None
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
        if results:
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
            raise typer.Exit(1)
    
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
            name for name in param_names 
            if getattr(ctx, name, None) is not None
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
            self.entity_class,
            self.entity_name,
            self.custom_filters,
            self.custom_output
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
