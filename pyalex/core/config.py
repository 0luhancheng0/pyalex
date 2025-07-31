"""Configuration management for PyAlex."""

try:
    from pyalex._version import __version__
except ImportError:
    __version__ = "0.0.0"


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


config = AlexConfig(
    email="0lh.cheng0@gmail.com",
    api_key=None,
    user_agent=f"pyalex/{__version__}",
    openalex_url="https://api.openalex.org",
    max_retries=DEFAULT_MAX_RETRIES,
    retry_backoff_factor=DEFAULT_RETRY_BACKOFF_FACTOR,
    retry_http_codes=DEFAULT_RETRY_HTTP_CODES,
    # Rate limiting configurations
    requests_per_second=DEFAULT_REQUESTS_PER_SECOND,
    requests_per_day=DEFAULT_REQUESTS_PER_DAY,
    rate_limit_buffer=DEFAULT_RATE_LIMIT_BUFFER,
    # CLI specific configurations
    cli_batch_size=DEFAULT_CLI_BATCH_SIZE,
    cli_max_width=CLI_MAX_WIDTH,
    cli_name_truncate_length=CLI_NAME_TRUNCATE_LENGTH,
    # HTTP client configurations
    total_timeout=DEFAULT_TOTAL_TIMEOUT,
    connect_timeout=DEFAULT_CONNECT_TIMEOUT,
    connection_limit=DEFAULT_CONNECTION_LIMIT,
    connection_limit_per_host=DEFAULT_CONNECTION_LIMIT_PER_HOST,
    max_concurrent=DEFAULT_MAX_CONCURRENT,
)
