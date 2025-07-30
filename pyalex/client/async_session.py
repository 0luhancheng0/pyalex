"""Async HTTP session management for OpenAlex API."""

import asyncio

try:
    import aiohttp
except ImportError:
    aiohttp = None

from pyalex.core.config import config


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
    headers = {'User-Agent': 'pyalex'}
    
    if config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"
    if config.email:
        headers["From"] = config.email
    if config.user_agent:
        headers["User-Agent"] = config.user_agent
    
    timeout = aiohttp.ClientTimeout(
        total=config.total_timeout, 
        connect=config.connect_timeout
    )
    connector = aiohttp.TCPConnector(
        limit=config.connection_limit, 
        limit_per_host=config.connection_limit_per_host
    )
    
    return aiohttp.ClientSession(
        timeout=timeout,
        connector=connector,
        headers=headers
    )


async def async_get_with_retry(session, url, max_retries=3, backoff_factor=1.0):
    """Make an async GET request with retry logic.

    Parameters
    ----------
    session : aiohttp.ClientSession
        Async session to use for the request.
    url : str
        URL to request.
    max_retries : int, optional
        Maximum number of retries.
    backoff_factor : float, optional
        Backoff factor for retries.

    Returns
    -------
    dict
        JSON response data.
    """
    if aiohttp is None:
        raise ImportError(
            "aiohttp is required for async functionality. "
            "Install with: pip install aiohttp"
        )
    
    for attempt in range(max_retries + 1):
        try:
            async with session.get(url) as response:
                if response.status == 403:
                    response_json = await response.json()
                    if (
                        isinstance(response_json.get("error"), str)
                        and "query parameters" in response_json["error"]
                    ):
                        from pyalex.core.response import QueryError
                        raise QueryError(response_json["message"])
                
                response.raise_for_status()
                return await response.json()
                
        except (aiohttp.ClientError, asyncio.TimeoutError):
            if attempt == max_retries:
                raise
            await asyncio.sleep(backoff_factor * (2 ** attempt))
    
    raise Exception(f"Failed to fetch {url} after {max_retries} retries")


async def async_batch_requests(urls, max_concurrent=None):
    if max_concurrent is None:
        max_concurrent = config.max_concurrent
    """Execute multiple async requests with concurrency control.

    Parameters
    ----------
    urls : list
        List of URLs to request.
    max_concurrent : int, optional
        Maximum number of concurrent requests.

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
    if max_concurrent is None:
        max_concurrent = config.max_concurrent
    """Execute multiple async requests with concurrency control and rich progress bar.

    Parameters
    ----------
    urls : list
        List of URLs to request.
    max_concurrent : int, optional
        Maximum number of concurrent requests.
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
    
    try:
        from rich.progress import (
            Progress, SpinnerColumn, TextColumn, BarColumn, 
            MofNCompleteColumn, TimeElapsedColumn
        )
        
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
