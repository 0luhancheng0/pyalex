"""HTTP session management for OpenAlex API."""

import requests
from urllib3.util import Retry


def get_requests_session(config=None):
    """Create a Requests session with automatic retry.

    Parameters
    ----------
    config : AlexConfig, optional
        Configuration object for OpenAlex API. If not provided, uses global config.

    Returns
    -------
    requests.Session
        Requests session with retry configuration.
    """
    if config is None:
        from pyalex.core.config import config as global_config
        config = global_config
    
    # create an Requests Session with automatic retry:
    requests_session = requests.Session()
    retries = Retry(
        total=config.max_retries,
        backoff_factor=config.retry_backoff_factor,
        status_forcelist=config.retry_http_codes,
        allowed_methods={"GET"},
    )
    requests_session.mount(
        "https://", requests.adapters.HTTPAdapter(max_retries=retries)
    )

    return requests_session
