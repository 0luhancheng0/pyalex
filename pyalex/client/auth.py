"""Authentication module for OpenAlex API."""

from requests.auth import AuthBase


class OpenAlexAuth(AuthBase):
    """OpenAlex auth class based on requests auth.

    Includes the email, api_key, and user-agent headers.

    Parameters
    ----------
    config : AlexConfig
        Configuration object for OpenAlex API.
    """

    def __init__(self, config):
        self.config = config

    def __call__(self, r):
        if self.config.api_key:
            r.headers["Authorization"] = f"Bearer {self.config.api_key}"

        if self.config.email:
            r.headers["From"] = self.config.email

        if self.config.user_agent:
            r.headers["User-Agent"] = self.config.user_agent

        return r
