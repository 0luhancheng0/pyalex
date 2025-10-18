"""
PyAlex Logging Configuration

This module provides centralized logging configuration for the PyAlex package.
It handles both library usage and CLI usage scenarios with appropriate log levels.
"""
import logging
import sys
from typing import Optional

# Package-level logger
logger = logging.getLogger('pyalex')

# Constants for log formatting
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
SIMPLE_FORMAT = '%(levelname)s: %(message)s'
DEBUG_FORMAT = '%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s'


def setup_logger(
    level: str = 'INFO',
    format_type: str = 'simple',
    stream: Optional[object] = None
) -> logging.Logger:
    """
    Set up the PyAlex logger with specified configuration.
    
    Parameters
    ----------
    level : str, default 'INFO'
        Logging level ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
    format_type : str, default 'simple' 
        Format type ('simple', 'detailed', 'debug')
    stream : object, optional
        Output stream (default: stderr for library, stdout for CLI)
        
    Returns
    -------
    logging.Logger
        Configured logger instance
    """
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Choose format based on type
    format_map = {
        'simple': SIMPLE_FORMAT,
        'detailed': LOG_FORMAT, 
        'debug': DEBUG_FORMAT
    }
    log_format = format_map.get(format_type, SIMPLE_FORMAT)
    
    # Set default stream based on usage context
    if stream is None:
        # Use stdout for CLI debug mode, stderr for library usage
        stream = sys.stderr
    
    # Remove existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create and configure handler
    handler = logging.StreamHandler(stream)
    handler.setLevel(numeric_level)
    formatter = logging.Formatter(log_format)
    handler.setFormatter(formatter)
    
    # Configure logger
    logger.setLevel(numeric_level)
    logger.addHandler(handler)
    logger.propagate = False  # Prevent duplicate messages
    
    return logger


def get_logger() -> logging.Logger:
    """
    Get the configured PyAlex logger.
    
    Returns
    -------
    logging.Logger
        The PyAlex logger instance
    """
    return logger


def setup_cli_logging(debug: bool = False) -> logging.Logger:
    """
    Set up logging specifically for CLI usage.
    
    Parameters
    ----------
    debug : bool, default False
        Whether to enable debug mode with verbose output
        
    Returns
    -------
    logging.Logger
        Configured logger for CLI usage
    """
    if debug:
        return setup_logger(
            level='DEBUG',
            format_type='debug', 
            stream=sys.stdout
        )
    else:
        return setup_logger(
            level='WARNING',
            format_type='simple',
            stream=sys.stderr
        )


def log_api_request(url: str) -> None:
    """
    Log an API request URL at debug level.
    
    Parameters
    ----------
    url : str
        The API URL being requested
    """
    logger.debug(f"API URL: {url}")


def log_api_response(results, response_type: str = "results") -> None:
    """
    Log information about API response at debug level.
    
    Parameters
    ----------
    results : object
        The API response object
    response_type : str, default "results"
        Type of response for logging context
    """
    if results is None:
        logger.debug(f"No {response_type} returned from API")
        return
        
    logger.debug(f"Response type: {type(results)}")
    
    if hasattr(results, '__len__'):
        try:
            length = len(results)
            logger.debug(f"Response length: {length}")
        except (TypeError, AttributeError):
            pass
    
    if hasattr(results, 'meta') and results.meta:
        count = results.meta.get('count')
        if count is not None:
            logger.debug(f"Total count from meta: {count:,}")


def log_error(error: Exception, context: str = "") -> None:
    """
    Log an error with optional context.
    
    Parameters
    ----------
    error : Exception
        The exception that occurred
    context : str, optional
        Additional context about where the error occurred
    """
    if context:
        logger.error(f"{context}: {error}")
    else:
        logger.error(str(error))


def log_debug_traceback(error: Exception) -> None:
    """
    Log full traceback at debug level.
    
    Parameters
    ----------
    error : Exception
        The exception for which to log traceback
    """
    logger.debug("Full traceback:", exc_info=True)


# Initialize default logger configuration for library usage
setup_logger(level='WARNING', format_type='simple')
