"""
State management for PyAlex CLI.

This module manages global state for the CLI including:
- Debug mode
- Dry run mode
- Batch size
- Progress tracking context
"""

from typing import Optional
from dataclasses import dataclass, field


@dataclass
class CLIState:
    """Global state for CLI operations."""
    
    debug_mode: bool = False
    dry_run_mode: bool = False
    batch_size: int = 100
    progress_context_depth: int = 0
    batch_progress_context: Optional[any] = None
    
    def is_debug(self) -> bool:
        """Check if debug mode is enabled."""
        return self.debug_mode
    
    def is_dry_run(self) -> bool:
        """Check if dry run mode is enabled."""
        return self.dry_run_mode
    
    def get_batch_size(self) -> int:
        """Get the configured batch size."""
        return self.batch_size
    
    def enter_progress_context(self) -> int:
        """
        Enter a progress context (increment depth).
        
        Returns:
            New context depth
        """
        self.progress_context_depth += 1
        return self.progress_context_depth
    
    def exit_progress_context(self) -> int:
        """
        Exit a progress context (decrement depth).
        
        Returns:
            New context depth
        """
        if self.progress_context_depth > 0:
            self.progress_context_depth -= 1
        return self.progress_context_depth
    
    def is_progress_active(self) -> bool:
        """Check if we're currently in a progress context."""
        return self.progress_context_depth > 0
    
    def should_show_progress(self) -> bool:
        """Determine if progress should be shown."""
        return self.progress_context_depth <= 1
    
    def set_batch_progress(self, context: Optional[any]) -> None:
        """
        Set the batch progress context.
        
        Args:
            context: Progress context object
        """
        self.batch_progress_context = context
    
    def get_batch_progress(self) -> Optional[any]:
        """Get the current batch progress context."""
        return self.batch_progress_context
    
    def is_in_batch_context(self) -> bool:
        """Check if we're in a batch operation context."""
        return self.batch_progress_context is not None
    
    def reset(self) -> None:
        """Reset state to defaults."""
        self.debug_mode = False
        self.dry_run_mode = False
        self.batch_size = 100
        self.progress_context_depth = 0
        self.batch_progress_context = None


# Global CLI state instance
_cli_state = CLIState()


def get_state() -> CLIState:
    """
    Get the global CLI state instance.
    
    Returns:
        Global CLIState instance
    """
    return _cli_state


def set_state(debug_mode: bool = False, dry_run_mode: bool = False, 
              batch_size: int = 100) -> None:
    """
    Configure the global CLI state.
    
    Args:
        debug_mode: Enable debug output
        dry_run_mode: Enable dry run mode
        batch_size: Batch size for operations
    """
    _cli_state.debug_mode = debug_mode
    _cli_state.dry_run_mode = dry_run_mode
    _cli_state.batch_size = batch_size


def is_debug() -> bool:
    """Check if debug mode is enabled."""
    return _cli_state.is_debug()


def is_dry_run() -> bool:
    """Check if dry run mode is enabled."""
    return _cli_state.is_dry_run()


def get_batch_size() -> int:
    """Get the configured batch size."""
    return _cli_state.get_batch_size()


def enter_progress_context() -> int:
    """Enter a progress tracking context."""
    return _cli_state.enter_progress_context()


def exit_progress_context() -> int:
    """Exit a progress tracking context."""
    return _cli_state.exit_progress_context()


def is_progress_active() -> bool:
    """Check if progress tracking is currently active."""
    return _cli_state.is_progress_active()


def should_show_progress() -> bool:
    """Check if progress should be displayed."""
    return _cli_state.should_show_progress()


def set_batch_progress_context(context: Optional[any]) -> None:
    """Set the batch progress context."""
    _cli_state.set_batch_progress(context)


def get_batch_progress_context() -> Optional[any]:
    """Get the batch progress context."""
    return _cli_state.get_batch_progress()


def is_in_batch_context() -> bool:
    """Check if we're in a batch operation."""
    return _cli_state.is_in_batch_context()


def reset_state() -> None:
    """Reset state to defaults."""
    _cli_state.reset()
