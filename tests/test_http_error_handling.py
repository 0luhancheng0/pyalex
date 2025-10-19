"""Unit tests for HTTP client error handling refactoring."""

from unittest.mock import Mock

import httpx
import pytest

from pyalex.client.httpx_session import _handle_403_error
from pyalex.client.httpx_session import _handle_non_retryable_error
from pyalex.client.httpx_session import _handle_retryable_error
from pyalex.exceptions import APIError
from pyalex.exceptions import RateLimitError


class TestHandle403Error:
    """Tests for _handle_403_error helper function."""

    def test_403_with_query_parameter_error(self):
        """Test 403 error with query parameter issue."""
        response = Mock(spec=httpx.Response)
        response.json = Mock(
            return_value={
                "error": "query parameters are invalid",
                "message": "Invalid parameter: xyz",
            }
        )

        from pyalex.core.response import QueryError

        with pytest.raises(QueryError):
            _handle_403_error(response)

    def test_403_without_query_parameter_error(self):
        """Test 403 error without query parameter issue."""
        response = Mock()
        response.json.return_value = {"error": "forbidden", "message": "Access denied"}

        # Should not raise, just pass through
        _handle_403_error(response)

    def test_403_with_invalid_json(self):
        """Test 403 error with invalid JSON response."""
        response = Mock()
        response.json.side_effect = ValueError("Invalid JSON")

        # Should not raise, just pass through
        _handle_403_error(response)

    def test_403_with_missing_fields(self):
        """Test 403 error with missing fields in JSON."""
        response = Mock()
        response.json.return_value = {"error": "some error"}

        # Should not raise, just pass through
        _handle_403_error(response)


class TestHandleRetryableError:
    """Tests for _handle_retryable_error helper function."""

    def test_rate_limit_with_retry_after_header(self):
        """Test rate limit error with Retry-After header."""
        import asyncio

        response = Mock()
        response.status_code = 429
        response.headers = {"Retry-After": "60"}

        sleep_time = asyncio.run(
            _handle_retryable_error(
                response,
                attempt=0,
                max_retries=3,
                backoff_factor=2.0,
                url="http://test",
            )
        )
        assert sleep_time == 60

    def test_rate_limit_without_retry_after_header(self):
        """Test rate limit error without Retry-After header."""
        import asyncio

        response = Mock()
        response.status_code = 429
        response.headers = {}

        sleep_time = asyncio.run(
            _handle_retryable_error(
                response,
                attempt=1,
                max_retries=3,
                backoff_factor=2.0,
                url="http://test",
            )
        )
        # Should use exponential backoff: 2.0 * (2 ** 2) = 8.0
        assert sleep_time == 8.0

    def test_rate_limit_max_retries_reached(self):
        """Test rate limit error when max retries reached."""
        import asyncio

        response = Mock()
        response.status_code = 429
        response.headers = {}
        response.text = "Rate limit exceeded"

        with pytest.raises(RateLimitError, match="Rate limit exceeded"):
            asyncio.run(
                _handle_retryable_error(
                    response,
                    attempt=3,
                    max_retries=3,
                    backoff_factor=2.0,
                    url="http://test",
                )
            )

    def test_server_error_retryable(self):
        """Test server error (500) that should be retried."""
        import asyncio

        response = Mock()
        response.status_code = 503
        response.text = "Service unavailable"

        sleep_time = asyncio.run(
            _handle_retryable_error(
                response,
                attempt=0,
                max_retries=3,
                backoff_factor=1.5,
                url="http://test",
            )
        )
        # Should use exponential backoff with jitter
        assert sleep_time >= 1.5 and sleep_time <= 1.6

    def test_server_error_max_retries_reached(self):
        """Test server error when max retries reached."""
        import asyncio

        response = Mock()
        response.status_code = 500
        response.text = "Internal server error"

        with pytest.raises(APIError, match="Server error"):
            asyncio.run(
                _handle_retryable_error(
                    response,
                    attempt=3,
                    max_retries=3,
                    backoff_factor=2.0,
                    url="http://test",
                )
            )

    def test_exponential_backoff_calculation(self):
        """Test exponential backoff calculation."""
        import asyncio

        response = Mock()
        response.status_code = 502
        response.text = "Bad gateway"

        # Test multiple attempts
        sleep_time_0 = asyncio.run(
            _handle_retryable_error(
                response,
                attempt=0,
                max_retries=5,
                backoff_factor=1.0,
                url="http://test",
            )
        )
        sleep_time_1 = asyncio.run(
            _handle_retryable_error(
                response,
                attempt=1,
                max_retries=5,
                backoff_factor=1.0,
                url="http://test",
            )
        )
        sleep_time_2 = asyncio.run(
            _handle_retryable_error(
                response,
                attempt=2,
                max_retries=5,
                backoff_factor=1.0,
                url="http://test",
            )
        )

        # Check exponential growth (allowing for jitter)
        assert sleep_time_0 >= 1.0 and sleep_time_0 <= 1.1
        assert sleep_time_1 >= 2.0 and sleep_time_1 <= 2.1
        assert sleep_time_2 >= 4.0 and sleep_time_2 <= 4.1


class TestHandleNonRetryableError:
    """Tests for _handle_non_retryable_error helper function."""

    def test_404_not_found(self):
        """Test 404 error handling."""
        response = Mock()
        response.status_code = 404
        response.text = "Not found"

        with pytest.raises(APIError, match="Resource not found"):
            _handle_non_retryable_error(response, url="http://test")

    def test_400_bad_request(self):
        """Test 400 error handling."""
        response = Mock()
        response.status_code = 400
        response.text = "Bad request"

        with pytest.raises(APIError, match="HTTP 400 error"):
            _handle_non_retryable_error(response, url="http://test")

    def test_401_unauthorized(self):
        """Test 401 error handling."""
        response = Mock()
        response.status_code = 401
        response.text = "Unauthorized"

        with pytest.raises(APIError, match="HTTP 401 error"):
            _handle_non_retryable_error(response, url="http://test")

    def test_403_forbidden(self):
        """Test 403 error handling."""
        response = Mock()
        response.status_code = 403
        response.text = "Forbidden"

        with pytest.raises(APIError, match="HTTP 403 error"):
            _handle_non_retryable_error(response, url="http://test")

    def test_500_server_error(self):
        """Test 500 error handling (categorized as server error)."""
        response = Mock()
        response.status_code = 500
        response.text = "Internal server error"

        with pytest.raises(APIError, match="Server error"):
            _handle_non_retryable_error(response, url="http://test")

    def test_error_message_truncation(self):
        """Test that error response text is truncated to 200 chars."""
        response = Mock()
        response.status_code = 400
        response.text = "x" * 500

        try:
            _handle_non_retryable_error(response, url="http://test")
        except APIError as e:
            # Check that response_text is truncated
            assert len(e.response_text) == 200

    def test_error_with_empty_response_text(self):
        """Test error with empty response text."""
        response = Mock()
        response.status_code = 404
        response.text = None

        with pytest.raises(APIError, match="Resource not found"):
            _handle_non_retryable_error(response, url="http://test")


class TestErrorHandlingIntegration:
    """Integration tests for error handling helpers."""

    def test_403_handler_doesnt_raise_on_non_query_errors(self):
        """Test that 403 handler only raises on query parameter errors."""
        response = Mock()
        response.json.return_value = {"error": "access denied", "message": "Forbidden"}

        # Should not raise
        try:
            _handle_403_error(response)
        except Exception as e:
            pytest.fail(f"Should not have raised: {e}")

    def test_retryable_handler_increases_backoff(self):
        """Test that retryable handler increases backoff with each attempt."""
        import asyncio

        response = Mock()
        response.status_code = 503
        response.text = "Service unavailable"

        times = []
        for attempt in range(3):
            sleep_time = asyncio.run(
                _handle_retryable_error(
                    response,
                    attempt=attempt,
                    max_retries=5,
                    backoff_factor=1.0,
                    url="http://test",
                )
            )
            times.append(sleep_time)

        # Each time should be roughly double the previous (allowing for jitter)
        assert times[1] > times[0]
        assert times[2] > times[1]
