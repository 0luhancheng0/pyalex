"""Work entities for OpenAlex API."""

import warnings

from pyalex.client.auth import OpenAlexAuth
from pyalex.client.session import get_requests_session
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

        res = get_requests_session().get(n_gram_url, auth=OpenAlexAuth(config))
        res.raise_for_status()
        results = res.json()

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
