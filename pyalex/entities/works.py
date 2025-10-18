"""Work entities for OpenAlex API."""

import asyncio
import warnings

from pyalex.client.auth import OpenAlexAuth
from pyalex.core.config import config
from pyalex.core.response import OpenAlexResponseList
from pyalex.core.utils import invert_abstract
from pyalex.entities.base import BaseOpenAlex


class Work(dict):
    """Class representing a work entity in OpenAlex."""

    def __getitem__(self, key):
        if key == "abstract":
            return invert_abstract(self["abstract_inverted_index"])

        return super().__getitem__(key)

    def ngrams(self, return_meta=False):
        """Get n-grams for the work.
        
        Uses async requests internally for optimal performance.

        Parameters
        ----------
        return_meta : bool, optional
            Whether to return metadata.

        Returns
        -------
        OpenAlexResponseList
            List of n-grams.
        """
        openalex_id = self["id"].split("/")[-1]
        n_gram_url = f"{config.openalex_url}/works/{openalex_id}/ngrams"

        # Use async method internally
        async def fetch_ngrams():
            from pyalex.client.httpx_session import async_get_with_retry, get_async_client
            async with await get_async_client() as client:
                results = await async_get_with_retry(client, n_gram_url)
                return results
        
        results = asyncio.run(fetch_ngrams())

        resp_list = OpenAlexResponseList(results["ngrams"], results["meta"])

        if return_meta:
            warnings.warn(
                "return_meta is deprecated, call .meta on the result",
                DeprecationWarning,
                stacklevel=2,
            )
            return resp_list, resp_list.meta
        else:
            return resp_list


class Works(BaseOpenAlex):
    """Class representing a collection of work entities in OpenAlex."""

    resource_class = Work
