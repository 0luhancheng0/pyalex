"""Async HTTP session management using httpx for PyAlex.

This module provides async HTTP client functionality using httpx with:
- HTTP/2 support
- Connection pooling
- Retry logic with exponential backoff
- Rate limiting
"""

import asyncio
import time
from typing import Any, Dict, List, Optional

import httpx

from pyalex.core.config import config
from pyalex.exceptions import NetworkError, APIError, RateLimitError


class RateLimiter:
    """Rate limiter for async requests."""
    
    def __init__(self, requests_per_second: float = 10.0):
        self.requests_per_second = requests_per_second
        self.min_interval = 1.0 / requests_per_second
        self.last_request_time = 0.0
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """Acquire permission to make a request, waiting if necessary."""
        async with self._lock:
            now = time.time()
            time_since_last = now - self.last_request_time
            if time_since_last < self.min_interval:
                sleep_time = self.min_interval - time_since_last
                await asyncio.sleep(sleep_time)
            self.last_request_time = time.time()


# Global rate limiter instance
_rate_limiter = None


def get_rate_limiter() -> RateLimiter:
    """Get or create the global rate limiter."""
    global _rate_limiter
    if _rate_limiter is None:
        rate_limit = config.requests_per_second * config.rate_limit_buffer
        _rate_limiter = RateLimiter(rate_limit)
    return _rate_limiter


async def get_async_client() -> httpx.AsyncClient:
    """Create an httpx async client for requests.

    Returns
    -------
    httpx.AsyncClient
        Async client with timeout and connection configuration.
    """
    if httpx is None:
        raise ImportError(
            "httpx is required for async functionality. "
            "Install with: pip install httpx"
        )
    
    # Build auth headers from config
    headers = {}
    
    if config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"
    if config.email:
        headers["From"] = config.email
    if config.user_agent:
        headers["User-Agent"] = config.user_agent
    else:
        headers["User-Agent"] = "pyalex"
    
    # Configure timeouts
    timeout = httpx.Timeout(
        connect=config.connect_timeout,
        read=config.total_timeout,
        write=config.total_timeout,
        pool=config.total_timeout
    )
    
    # Configure connection limits
    limits = httpx.Limits(
        max_connections=config.connection_limit,
        max_keepalive_connections=config.connection_limit_per_host
    )
    
    return httpx.AsyncClient(
        timeout=timeout,
        limits=limits,
        headers=headers,
        http2=True,  # Enable HTTP/2 support
        follow_redirects=True
    )


async def async_get_with_retry(
    client: httpx.AsyncClient, 
    url: str, 
    max_retries: Optional[int] = None, 
    backoff_factor: Optional[float] = None
) -> Dict[str, Any]:
    """Make an async GET request with retry logic and rate limiting.

    Parameters
    ----------
    client : httpx.AsyncClient
        Async client to use for the request.
    url : str
        URL to request.
    max_retries : int, optional
        Maximum number of retries. Uses config.max_retries if None.
    backoff_factor : float, optional
        Backoff factor for retries. Uses config.retry_backoff_factor if None.

    Returns
    -------
    dict
        JSON response data.

    Raises
    ------
    httpx.HTTPError
        If the request fails after all retries.
    QueryError
        If the request returns a 403 error with query parameter issues.
    """
    if max_retries is None:
        max_retries = config.max_retries
    if backoff_factor is None:
        backoff_factor = config.retry_backoff_factor
    
    rate_limiter = get_rate_limiter()
    retry_codes = set(config.retry_http_codes)
    
    for attempt in range(max_retries + 1):
        try:
            # Apply rate limiting
            await rate_limiter.acquire()
            
            response = await client.get(url)
            
            # Handle specific 403 errors for query parameter issues
            if response.status_code == 403:
                try:
                    response_json = response.json()
                    if (
                        isinstance(response_json.get("error"), str)
                        and "query parameters" in response_json["error"]
                    ):
                        from pyalex.core.response import QueryError
                        raise QueryError(response_json["message"])
                except (ValueError, KeyError):
                    pass  # Not a JSON response or missing fields
            
            # Check if we should retry based on status code
            if response.status_code in retry_codes:
                if response.status_code == 429:
                    # Rate limiting
                    retry_after = response.headers.get('Retry-After')
                    if attempt == max_retries:
                        raise RateLimitError(
                            "Rate limit exceeded",
                            retry_after=int(retry_after) if retry_after else None,
                            url=url,
                            response_text=response.text[:200] if response.text else None
                        )
                    sleep_time = int(retry_after) if retry_after else backoff_factor * (2 ** (attempt + 1))
                    await asyncio.sleep(sleep_time)
                    continue
                
                # Other retryable errors
                if attempt == max_retries:
                    error_msg = f"HTTP {response.status_code} error"
                    if response.status_code >= 500:
                        error_msg = "Server error"
                    raise APIError(
                        error_msg,
                        status_code=response.status_code,
                        url=url,
                        response_text=response.text[:200] if response.text else None
                    )
                
                # Calculate exponential backoff with jitter
                sleep_time = (
                    backoff_factor * (2 ** attempt) + 
                    (time.time() % 1) * 0.1
                )
                await asyncio.sleep(sleep_time)
                continue
            
            # Handle non-retryable errors
            if response.status_code >= 400:
                error_msg = f"HTTP {response.status_code} error"
                if response.status_code == 404:
                    error_msg = "Resource not found"
                elif response.status_code >= 500:
                    error_msg = "Server error"
                
                raise APIError(
                    error_msg,
                    status_code=response.status_code,
                    url=url,
                    response_text=response.text[:200] if response.text else None
                )
            
            # Success
            return response.json()
                
        except (httpx.RequestError, httpx.TimeoutException) as e:
            if attempt == max_retries:
                raise NetworkError(
                    f"Network error: {str(e)}",
                    url=url
                ) from e
            # Calculate exponential backoff with jitter for network errors
            sleep_time = (
                backoff_factor * (2 ** attempt) + 
                (time.time() % 1) * 0.1
            )
            await asyncio.sleep(sleep_time)
    
    # Should not reach here
    raise NetworkError(f"Failed to fetch {url} after {max_retries} retries", url=url)


async def async_batch_requests(
    urls: List[str], 
    max_concurrent: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Execute multiple async requests with concurrency control.

    Parameters
    ----------
    urls : list
        List of URLs to request.
    max_concurrent : int, optional
        Maximum number of concurrent requests. Uses config.max_concurrent if None.

    Returns
    -------
    list
        List of response data dictionaries.
    """
    if httpx is None:
        raise ImportError(
            "httpx is required for async functionality. "
            "Install with: pip install httpx"
        )
    
    if max_concurrent is None:
        max_concurrent = config.max_concurrent
    
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def fetch_with_semaphore(client, url):
        async with semaphore:
            return await async_get_with_retry(client, url)
    
    async with get_async_client() as client:
        tasks = [fetch_with_semaphore(client, url) for url in urls]
        return await asyncio.gather(*tasks)


async def async_batch_requests_with_progress(
    urls: List[str],
    max_concurrent: Optional[int] = None,
    description: str = "Fetching data"
) -> List[Dict[str, Any]]:
    """Execute multiple async requests with concurrency control and rich progress bar.

    Parameters
    ----------
    urls : list
        List of URLs to request.
    max_concurrent : int, optional
        Maximum number of concurrent requests. Uses config.max_concurrent if None.
    description : str, optional
        Description for the progress bar.

    Returns
    -------
    list
        List of response data dictionaries.
    """
    if httpx is None:
        raise ImportError(
            "httpx is required for async functionality. "
            "Install with: pip install httpx"
        )
    
    if max_concurrent is None:
        max_concurrent = config.max_concurrent
    
    try:
        from rich.progress import BarColumn
        from rich.progress import MofNCompleteColumn
        from rich.progress import Progress
        from rich.progress import SpinnerColumn
        from rich.progress import TextColumn
        from rich.progress import TimeElapsedColumn
        
        semaphore = asyncio.Semaphore(max_concurrent)
        results = [None] * len(urls)
        
        async def fetch_with_semaphore(client, url, index, progress, task_id):
            async with semaphore:
                result = await async_get_with_retry(client, url)
                results[index] = result
                progress.update(task_id, advance=1)
                return result
        
        async with get_async_client() as client:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                MofNCompleteColumn(),
                TimeElapsedColumn(),
            ) as progress:
                task_id = progress.add_task(description, total=len(urls))
                
                tasks = [
                    fetch_with_semaphore(client, url, i, progress, task_id)
                    for i, url in enumerate(urls)
                ]
                await asyncio.gather(*tasks)
                
            return results
            
    except ImportError:
        # Fall back to basic async requests without progress bar
        return await async_batch_requests(urls, max_concurrent)


# Compatibility wrapper for existing code using get_async_session
async def get_async_session():
    """
    Compatibility wrapper for existing code.
    Returns an httpx.AsyncClient instead of aiohttp.ClientSession.
    
    Note: This is a context manager that should be used with async with.
    """
    return await get_async_client()
