"""
CLI formatting utilities for PyAlex.

This module handles all output formatting for the CLI, including:
- Table formatting
- JSON output
- Progress displays
- Debug messages
"""

from typing import Any, Dict, List, Optional
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich import print as rprint

console = Console()


def print_debug(message: str, level: str = "INFO") -> None:
    """
    Print debug message with color coding.
    
    Args:
        message: The debug message to print
        level: The severity level (INFO, WARNING, ERROR, DEBUG, STRATEGY)
    """
    colors = {
        "INFO": "cyan",
        "WARNING": "yellow",
        "ERROR": "red",
        "DEBUG": "magenta",
        "STRATEGY": "green",
    }
    color = colors.get(level, "white")
    rprint(f"[{color}][{level}][/{color}] {message}")


def print_dry_run_query(query_description: str, url: Optional[str] = None, 
                        estimated_queries: Optional[int] = None) -> None:
    """
    Print dry-run information about a query.
    
    Args:
        query_description: Description of the query
        url: Optional URL that would be queried
        estimated_queries: Optional number of estimated queries
    """
    rprint(f"\n[bold yellow]DRY RUN:[/bold yellow] {query_description}")
    if url:
        rprint(f"  [cyan]URL:[/cyan] {url}")
    if estimated_queries:
        rprint(f"  [cyan]Estimated queries:[/cyan] {estimated_queries}")


def print_debug_url(query: Any) -> None:
    """
    Print the URL for a query.
    
    Args:
        query: The query object to print URL for
    """
    try:
        url = query.url
        rprint(f"\n[bold cyan]Query URL:[/bold cyan]\n{url}\n")
    except Exception as e:
        rprint(f"[yellow]Could not construct URL: {e}[/yellow]")


def print_debug_results(results: List[Dict]) -> None:
    """
    Print debug information about results.
    
    Args:
        results: List of result dictionaries
    """
    rprint(f"[cyan]Retrieved {len(results)} results[/cyan]")


def show_simple_progress(description: str, current: int, total: int) -> None:
    """
    Show simple progress indication.
    
    Args:
        description: Progress description
        current: Current progress value
        total: Total progress value
    """
    percentage = (current / total * 100) if total > 0 else 0
    rprint(f"[cyan]{description}:[/cyan] {current:,}/{total:,} ({percentage:.0f}%)")


def create_table(title: str, columns: List[str]) -> Table:
    """
    Create a Rich table with standard styling.
    
    Args:
        title: Table title
        columns: List of column names
        
    Returns:
        Configured Rich Table object
    """
    table = Table(title=title, show_header=True, header_style="bold magenta")
    for col in columns:
        table.add_column(col, style="cyan", no_wrap=False)
    return table


def truncate_text(text: str, max_length: int = 50) -> str:
    """
    Truncate text to max length with ellipsis.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        
    Returns:
        Truncated text
    """
    if not text:
        return ""
    return text if len(text) <= max_length else f"{text[:max_length-3]}..."


def format_count(count: int) -> str:
    """
    Format a count with thousand separators.
    
    Args:
        count: Number to format
        
    Returns:
        Formatted string
    """
    return f"{count:,}"


def create_progress() -> Progress:
    """
    Create a Rich Progress bar with standard configuration.
    
    Returns:
        Configured Progress object
    """
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    )


def print_error(message: str) -> None:
    """
    Print an error message.
    
    Args:
        message: Error message to print
    """
    rprint(f"[bold red]Error:[/bold red] {message}")


def print_warning(message: str) -> None:
    """
    Print a warning message.
    
    Args:
        message: Warning message to print
    """
    rprint(f"[bold yellow]Warning:[/bold yellow] {message}")


def print_success(message: str) -> None:
    """
    Print a success message.
    
    Args:
        message: Success message to print
    """
    rprint(f"[bold green]✓[/bold green] {message}")


def print_info(message: str) -> None:
    """
    Print an info message.
    
    Args:
        message: Info message to print
    """
    rprint(f"[cyan]ℹ[/cyan] {message}")
