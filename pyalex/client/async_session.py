"""Async HTTP session management for OpenAlex API."""

import asyncio
import time

try:
    import aiohttp
except ImportError:
    aiohttp = None

from pyalex.core.config import config


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


async def get_async_session():
    """Create an aiohttp session for async requests.

    Returns
    -------
    aiohttp.ClientSession
        Async session with timeout and retry configuration.
    """
    if aiohttp is None:
        raise ImportError(
            "aiohttp is required for async functionality. "
            "Install with: pip install aiohttp"
        )

    # Get auth headers from config
    from pyalex.core.config import config

    headers = {"User-Agent": "pyalex"}

    if config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"
    if config.email:
        headers["From"] = config.email
    if config.user_agent:
        headers["User-Agent"] = config.user_agent

    timeout = aiohttp.ClientTimeout(
        total=config.total_timeout, connect=config.connect_timeout
    )
    connector = aiohttp.TCPConnector(
        limit=config.connection_limit, limit_per_host=config.connection_limit_per_host
    )

    return aiohttp.ClientSession(timeout=timeout, connector=connector, headers=headers)


async def async_get_with_retry(session, url, max_retries=None, backoff_factor=None):
    """Make an async GET request with retry logic and rate limiting.

    Parameters
    ----------
    session : aiohttp.ClientSession
        Async session to use for the request.
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
    aiohttp.ClientError
        If the request fails after all retries.
    QueryError
        If the request returns a 403 error with query parameter issues.
    """
    if aiohttp is None:
        raise ImportError(
            "aiohttp is required for async functionality. "
            "Install with: pip install aiohttp"
        )

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

            async with session.get(url) as response:
                # Handle specific 403 errors for query parameter issues
                if response.status == 403:
                    response_json = await response.json()
                    if (
                        isinstance(response_json.get("error"), str)
                        and "query parameters" in response_json["error"]
                    ):
                        from pyalex.core.response import QueryError

                        raise QueryError(response_json["message"])

                # Check if we should retry based on status code
                if response.status in retry_codes:
                    if attempt == max_retries:
                        response.raise_for_status()
                    # Calculate exponential backoff with jitter
                    sleep_time = backoff_factor * (2**attempt) + (time.time() % 1) * 0.1
                    await asyncio.sleep(sleep_time)
                    continue

                # Raise for other HTTP errors
                response.raise_for_status()
                return await response.json()

        except (aiohttp.ClientError, asyncio.TimeoutError):
            if attempt == max_retries:
                raise
            # Calculate exponential backoff with jitter for network errors
            sleep_time = backoff_factor * (2**attempt) + (time.time() % 1) * 0.1
            await asyncio.sleep(sleep_time)

    raise aiohttp.ClientError(f"Failed to fetch {url} after {max_retries} retries")


async def async_batch_requests(urls, max_concurrent=None):
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
    if aiohttp is None:
        raise ImportError(
            "aiohttp is required for async functionality. "
            "Install with: pip install aiohttp"
        )

    if max_concurrent is None:
        max_concurrent = config.max_concurrent

    semaphore = asyncio.Semaphore(max_concurrent)

    async def fetch_with_semaphore(session, url):
        async with semaphore:
            return await async_get_with_retry(session, url)

    session = await get_async_session()
    try:
        tasks = [fetch_with_semaphore(session, url) for url in urls]
        return await asyncio.gather(*tasks)
    finally:
        await session.close()


async def async_batch_requests_with_progress(
    urls, max_concurrent=None, description="Fetching data"
):
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
    if aiohttp is None:
        raise ImportError(
            "aiohttp is required for async functionality. "
            "Install with: pip install aiohttp"
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

        async def fetch_with_semaphore(session, url, index, progress, task_id):
            async with semaphore:
                result = await async_get_with_retry(session, url)
                results[index] = result
                progress.update(task_id, advance=1)
                return result

        session = await get_async_session()
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                MofNCompleteColumn(),
                TimeElapsedColumn(),
            ) as progress:
                task_id = progress.add_task(description, total=len(urls))

                tasks = [
                    fetch_with_semaphore(session, url, i, progress, task_id)
                    for i, url in enumerate(urls)
                ]
                await asyncio.gather(*tasks)

            return results
        finally:
            await session.close()

    except ImportError:
        # Fall back to basic async requests without progress bar
        return await async_batch_requests(urls, max_concurrent)
