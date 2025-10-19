"""
Custom exception classes for PyAlex.

This module defines specific exception types for different error scenarios,
enabling better error handling and more informative error messages.
"""


class PyAlexException(Exception):
    """Base exception class for all PyAlex errors."""

    def __init__(self, message: str, details: str | None = None):
        """
        Initialize PyAlex exception.

        Args:
            message: Main error message
            details: Optional additional details
        """
        self.message = message
        self.details = details
        super().__init__(self.format_message())

    def format_message(self) -> str:
        """Format the complete error message."""
        if self.details:
            return f"{self.message}\nDetails: {self.details}"
        return self.message


class NetworkError(PyAlexException):
    """
    Raised when network-related errors occur.

    Examples:
        - Connection timeout
        - DNS resolution failure
        - Network unreachable
    """

    def __init__(
        self, message: str, url: str | None = None, status_code: int | None = None
    ):
        """
        Initialize network error.

        Args:
            message: Error message
            url: URL that caused the error
            status_code: HTTP status code if applicable
        """
        self.url = url
        self.status_code = status_code

        details = []
        if url:
            details.append(f"URL: {url}")
        if status_code:
            details.append(f"Status: {status_code}")

        detail_str = ", ".join(details) if details else None
        super().__init__(message, detail_str)


class APIError(PyAlexException):
    """
    Raised when OpenAlex API returns an error.

    Examples:
        - 400 Bad Request
        - 404 Not Found
        - 429 Rate Limit Exceeded
        - 500 Internal Server Error
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_text: str | None = None,
        url: str | None = None,
    ):
        """
        Initialize API error.

        Args:
            message: Error message
            status_code: HTTP status code
            response_text: Response body text
            url: URL that was requested
        """
        self.status_code = status_code
        self.response_text = response_text
        self.url = url

        details = []
        if status_code:
            details.append(f"Status: {status_code}")
        if url:
            details.append(f"URL: {url}")
        if response_text and len(response_text) < 200:
            details.append(f"Response: {response_text}")

        detail_str = ", ".join(details) if details else None
        super().__init__(message, detail_str)


class RateLimitError(APIError):
    """
    Raised when rate limit is exceeded.

    The OpenAlex API has rate limits:
    - 10 requests per second (anonymous)
    - 100,000 requests per day
    """

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: int | None = None,
        **kwargs,
    ):
        """
        Initialize rate limit error.

        Args:
            message: Error message
            retry_after: Seconds to wait before retrying
            **kwargs: Additional arguments for APIError
        """
        self.retry_after = retry_after
        if retry_after:
            message = f"{message}. Retry after {retry_after} seconds."
        super().__init__(message, status_code=429, **kwargs)


class ValidationError(PyAlexException):
    """
    Raised when input validation fails.

    Examples:
        - Invalid date format
        - Invalid OpenAlex ID format
        - Invalid filter value
        - Mutually exclusive options provided
    """

    def __init__(
        self, message: str, field: str | None = None, value: str | None = None
    ):
        """
        Initialize validation error.

        Args:
            message: Error message
            field: Field that failed validation
            value: Invalid value
        """
        self.field = field
        self.value = value

        details = []
        if field:
            details.append(f"Field: {field}")
        if value:
            details.append(f"Value: {value}")

        detail_str = ", ".join(details) if details else None
        super().__init__(message, detail_str)


class ConfigurationError(PyAlexException):
    """
    Raised when configuration is invalid or missing.

    Examples:
        - Missing required configuration
        - Invalid configuration value
        - Configuration file not found
    """

    def __init__(self, message: str, config_key: str | None = None):
        """
        Initialize configuration error.

        Args:
            message: Error message
            config_key: Configuration key that caused the error
        """
        self.config_key = config_key
        detail_str = f"Key: {config_key}" if config_key else None
        super().__init__(message, detail_str)


class QueryError(PyAlexException):
    """
    Raised when a query is malformed or invalid.

    Examples:
        - Invalid filter syntax
        - Unsupported operation
        - Invalid sort field
    """

    def __init__(self, message: str, query: str | None = None):
        """
        Initialize query error.

        Args:
            message: Error message
            query: Query that caused the error
        """
        self.query = query
        detail_str = f"Query: {query}" if query else None
        super().__init__(message, detail_str)


class DataError(PyAlexException):
    """
    Raised when data processing fails.

    Examples:
        - Unexpected data format
        - Missing required fields
        - Data parsing error
    """

    def __init__(self, message: str, data_type: str | None = None):
        """
        Initialize data error.

        Args:
            message: Error message
            data_type: Type of data being processed
        """
        self.data_type = data_type
        detail_str = f"Type: {data_type}" if data_type else None
        super().__init__(message, detail_str)


class CLIError(PyAlexException):
    """
    Raised when CLI-specific errors occur.

    Examples:
        - Invalid command-line argument
        - File not found
        - Output file write error
    """

    def __init__(self, message: str, command: str | None = None):
        """
        Initialize CLI error.

        Args:
            message: Error message
            command: Command that caused the error
        """
        self.command = command
        detail_str = f"Command: {command}" if command else None
        super().__init__(message, detail_str)


# Convenience functions for common error scenarios


def raise_network_error(
    message: str, url: str | None = None, status_code: int | None = None
) -> None:
    """
    Raise a NetworkError with formatted message.

    Args:
        message: Error message
        url: URL that caused the error
        status_code: HTTP status code

    Raises:
        NetworkError
    """
    raise NetworkError(message, url=url, status_code=status_code)


def raise_api_error(
    message: str,
    status_code: int | None = None,
    response_text: str | None = None,
    url: str | None = None,
) -> None:
    """
    Raise an APIError with formatted message.

    Args:
        message: Error message
        status_code: HTTP status code
        response_text: Response body
        url: URL that was requested

    Raises:
        APIError
    """
    raise APIError(
        message, status_code=status_code, response_text=response_text, url=url
    )


def raise_validation_error(
    message: str, field: str | None = None, value: str | None = None
) -> None:
    """
    Raise a ValidationError with formatted message.

    Args:
        message: Error message
        field: Field that failed validation
        value: Invalid value

    Raises:
        ValidationError
    """
    raise ValidationError(message, field=field, value=value)
