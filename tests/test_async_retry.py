"""Test for async session retry mechanism and rate limiting."""

import asyncio
import time

import pytest

from pyalex.client.async_session import RateLimiter
from pyalex.client.async_session import get_rate_limiter
from pyalex.core.config import config


def test_rate_limiter_init():
    """Test rate limiter initialization."""
    limiter = RateLimiter(requests_per_second=5.0)
    assert limiter.requests_per_second == 5.0
    assert limiter.min_interval == 0.2  # 1/5
    assert limiter.last_request_time == 0.0


def test_rate_limiter_enforces_delay():
    """Test that rate limiter enforces proper delays."""
    async def _test():
        limiter = RateLimiter(requests_per_second=10.0)  # 0.1 second intervals
        
        await limiter.acquire()
        first_acquire = time.time()
        
        await limiter.acquire()
        second_acquire = time.time()
        
        # Second acquire should be delayed by at least min_interval
        delay = second_acquire - first_acquire
        assert delay >= 0.09  # Allow for small timing variations
    
    asyncio.run(_test())


def test_config_rate_limiting_defaults():
    """Test that rate limiting configuration is properly set."""
    assert config.requests_per_second == 10
    assert config.requests_per_day == 100000
    assert config.rate_limit_buffer == 0.9
    assert config.max_retries == 3
    assert config.retry_backoff_factor == 0.5
    assert 429 in config.retry_http_codes
    assert 500 in config.retry_http_codes
    assert 502 in config.retry_http_codes
    assert 503 in config.retry_http_codes
    assert 504 in config.retry_http_codes


def test_get_rate_limiter_singleton():
    """Test that get_rate_limiter returns singleton instance."""
    limiter1 = get_rate_limiter()
    limiter2 = get_rate_limiter()
    assert limiter1 is limiter2
    
    # Check that it respects config with buffer
    expected_rate = config.requests_per_second * config.rate_limit_buffer
    assert limiter1.requests_per_second == expected_rate


def test_async_config_integration():
    """Test that async configuration values are properly integrated."""
    # Test that we have sensible defaults for OpenAlex API
    assert config.max_retries >= 3, "Should retry at least 3 times for reliability"
    assert config.retry_backoff_factor > 0, "Should have positive backoff factor"
    assert config.requests_per_second <= 10, "Should not exceed OpenAlex rate limit"
    assert config.rate_limit_buffer < 1.0, "Should use buffer to stay under limit"
    
    # Test rate limiter respects configuration
    rate_limiter = get_rate_limiter()
    expected_rate = config.requests_per_second * config.rate_limit_buffer
    assert rate_limiter.requests_per_second == expected_rate
    assert rate_limiter.min_interval == 1.0 / expected_rate


if __name__ == "__main__":
    pytest.main([__file__])
