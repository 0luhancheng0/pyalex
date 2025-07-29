"""Client module for OpenAlex API."""

from .auth import OpenAlexAuth
from .session import get_requests_session

__all__ = ["OpenAlexAuth", "get_requests_session"]
