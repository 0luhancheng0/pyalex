"""Configuration management for PyAlex."""

import os
from pathlib import Path

try:
    from pyalex._version import __version__
except ImportError:
    __version__ = "0.0.0"

# Try to load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv

    # Load .env from current directory or parent directories
    load_dotenv(dotenv_path=Path.cwd() / ".env", verbose=False)
except ImportError:
    pass  # python-dotenv not installed, use environment variables as-is


# Constants
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_BACKOFF_FACTOR = 0.5
DEFAULT_RETRY_HTTP_CODES = [429, 500, 502, 503, 504]

# Rate Limiting (OpenAlex API limits)
DEFAULT_REQUESTS_PER_SECOND = 10  # OpenAlex allows max 10 requests per second
DEFAULT_REQUESTS_PER_DAY = 100000  # OpenAlex allows max 100,000 requests per day
DEFAULT_RATE_LIMIT_BUFFER = 0.9  # Use 90% of rate limit to stay safe

# API Limits and Thresholds
MAX_PER_PAGE = 200
MIN_PER_PAGE = 1
MAX_RECORD_IDS = 100
LARGE_QUERY_THRESHOLD = 10000
DEFAULT_MAX_RESULTS = 10000

# Pagination Defaults
CURSOR_START_VALUE = "*"
PAGE_START_VALUE = 1

# CLI Defaults
DEFAULT_CLI_BATCH_SIZE = 100
CLI_MAX_WIDTH = 150

# HTTP Client Defaults
DEFAULT_TOTAL_TIMEOUT = 30
DEFAULT_CONNECT_TIMEOUT = 10
DEFAULT_CONNECTION_LIMIT = 20
DEFAULT_CONNECTION_LIMIT_PER_HOST = 10
DEFAULT_MAX_CONCURRENT = 10

# CLI Display Defaults
CLI_NAME_TRUNCATE_LENGTH = 50

# Data version defaults
DEFAULT_DATA_VERSION = os.getenv("OPENALEX_DATA_VERSION", "2")
DEFAULT_INCLUDE_XPAC = os.getenv("OPENALEX_INCLUDE_XPAC", "true")


class AlexConfig(dict):
    """Configuration class for OpenAlex API.

    Attributes
    ----------
    email : str
        Email address for API requests.
    api_key : str
        API key for authentication.
    user_agent : str
        User agent string for API requests.
    openalex_url : str
        Base URL for OpenAlex API.
    max_retries : int
        Maximum number of retries for API requests.
    retry_backoff_factor : float
        Backoff factor for retries.
    retry_http_codes : list
        List of HTTP status codes to retry on.
    requests_per_second : int
        Maximum requests per second (OpenAlex rate limit: 10/sec).
    requests_per_day : int
        Maximum requests per day (OpenAlex rate limit: 100,000/day).
    rate_limit_buffer : float
        Buffer factor for rate limiting (e.g., 0.9 = use 90% of limit).
    """

    def __getattr__(self, key):
        return super().__getitem__(key)

    def __setattr__(self, key, value):
        return super().__setitem__(key, value)


def _get_env_int(key: str, default: int) -> int:
    """Get integer from environment variable with validation."""
    value = os.getenv(key)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        import warnings

        warnings.warn(
            f"Invalid integer for {key}: {value}. Using default: {default}",
            stacklevel=2,
        )
        return default


def _get_env_float(key: str, default: float) -> float:
    """Get float from environment variable with validation."""
    value = os.getenv(key)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        import warnings

        warnings.warn(
            f"Invalid float for {key}: {value}. Using default: {default}",
            stacklevel=2,
        )
        return default


config = AlexConfig(
    # Environment variables override defaults
    email=os.getenv("OPENALEX_EMAIL", "0lh.cheng0@gmail.com"),
    api_key=os.getenv("OPENALEX_API_KEY", None),
    user_agent=os.getenv("OPENALEX_USER_AGENT", f"pyalex/{__version__}"),
    openalex_url=os.getenv("OPENALEX_URL", "https://api.openalex.org"),
    max_retries=_get_env_int("OPENALEX_MAX_RETRIES", DEFAULT_MAX_RETRIES),
    retry_backoff_factor=_get_env_float(
        "OPENALEX_RETRY_BACKOFF", DEFAULT_RETRY_BACKOFF_FACTOR
    ),
    retry_http_codes=DEFAULT_RETRY_HTTP_CODES,
    # Rate limiting configurations
    requests_per_second=_get_env_float(
        "OPENALEX_RATE_LIMIT", DEFAULT_REQUESTS_PER_SECOND
    ),
    requests_per_day=_get_env_int(
        "OPENALEX_REQUESTS_PER_DAY", DEFAULT_REQUESTS_PER_DAY
    ),
    rate_limit_buffer=_get_env_float("OPENALEX_RATE_BUFFER", DEFAULT_RATE_LIMIT_BUFFER),
    # CLI specific configurations
    cli_batch_size=_get_env_int("OPENALEX_CLI_BATCH_SIZE", DEFAULT_CLI_BATCH_SIZE),
    cli_max_width=_get_env_int("OPENALEX_CLI_MAX_WIDTH", CLI_MAX_WIDTH),
    cli_name_truncate_length=_get_env_int(
        "OPENALEX_CLI_NAME_LENGTH", CLI_NAME_TRUNCATE_LENGTH
    ),
    # HTTP client configurations
    total_timeout=_get_env_float("OPENALEX_TOTAL_TIMEOUT", DEFAULT_TOTAL_TIMEOUT),
    connect_timeout=_get_env_float("OPENALEX_CONNECT_TIMEOUT", DEFAULT_CONNECT_TIMEOUT),
    connection_limit=_get_env_int(
        "OPENALEX_CONNECTION_LIMIT", DEFAULT_CONNECTION_LIMIT
    ),
    connection_limit_per_host=_get_env_int(
        "OPENALEX_CONNECTION_LIMIT_PER_HOST", DEFAULT_CONNECTION_LIMIT_PER_HOST
    ),
    max_concurrent=_get_env_int("OPENALEX_MAX_CONCURRENT", DEFAULT_MAX_CONCURRENT),
    data_version=DEFAULT_DATA_VERSION,
    include_xpac=DEFAULT_INCLUDE_XPAC,
)
