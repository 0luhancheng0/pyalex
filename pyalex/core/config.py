"""Configuration management for PyAlex."""

try:
    from pyalex._version import __version__
except ImportError:
    __version__ = "0.0.0"


# Constants
DEFAULT_MAX_RETRIES = 0
DEFAULT_RETRY_BACKOFF_FACTOR = 0.1
DEFAULT_RETRY_HTTP_CODES = [429, 500, 503]

# API Limits and Thresholds
MAX_PER_PAGE = 200
MIN_PER_PAGE = 1
MAX_RECORD_IDS = 100
LARGE_QUERY_THRESHOLD = 10000
DEFAULT_MAX_RESULTS = 10000

# Pagination Defaults
CURSOR_START_VALUE = "*"
PAGE_START_VALUE = 1


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
)
