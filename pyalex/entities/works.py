"""Work entities for OpenAlex API."""

import asyncio
import warnings

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
            from pyalex.client.httpx_session import async_get_with_retry
            from pyalex.client.httpx_session import get_async_client

            async with await get_async_client() as client:
                results = await async_get_with_retry(client, n_gram_url)
                return results

        results = asyncio.run(fetch_ngrams())

        resp_list = OpenAlexResponseList(results["ngrams"], results["meta"])

        if return_meta:
            warnings.warn(
                "return_meta is deprecated, access metadata via .attrs['meta']",
                DeprecationWarning,
                stacklevel=2,
            )
            meta = (
                resp_list.attrs.get("meta", {}) if hasattr(resp_list, "attrs") else {}
            )
            return resp_list, meta
        else:
            return resp_list


class Works(BaseOpenAlex):
    """Class representing a collection of work entities in OpenAlex."""

    resource_class = Work

    def filter_by_author(self, author_id, **kwargs):
        """Filter works by author OpenAlex ID.

        Parameters
        ----------
        author_id : str or list
            OpenAlex ID(s) of the author(s). Can be a single ID or a list for OR logic.
        **kwargs : dict
            Additional filter parameters.

        Returns
        -------
        Works
            Updated Works object.

        Examples
        --------
        >>> Works().filter_by_author("A2208157607")
        >>> Works().filter_by_author(["A2208157607", "A5023888391"])
        """
        if isinstance(author_id, list):
            # Multiple authors - use OR logic
            id_filter = "|".join(author_id)
            return self.filter(authorships={"author": {"id": id_filter}}, **kwargs)
        return self.filter(authorships={"author": {"id": author_id}}, **kwargs)

    def filter_by_institution(self, institution_id, **kwargs):
        """Filter works by institution OpenAlex ID.

        Parameters
        ----------
        institution_id : str or list
            OpenAlex ID(s) of the institution(s). Can be a single ID or a list for OR logic.
        **kwargs : dict
            Additional filter parameters.

        Returns
        -------
        Works
            Updated Works object.

        Examples
        --------
        >>> Works().filter_by_institution("I27837315")
        >>> Works().filter_by_institution(["I27837315", "I5709307"])
        """
        if isinstance(institution_id, list):
            # Multiple institutions - use OR logic
            id_filter = "|".join(institution_id)
            return self.filter(
                authorships={"institutions": {"id": id_filter}}, **kwargs
            )
        return self.filter(
            authorships={"institutions": {"id": institution_id}}, **kwargs
        )

    def filter_by_source(self, source_id, **kwargs):
        """Filter works by source (journal/venue) OpenAlex ID.

        Parameters
        ----------
        source_id : str or list
            OpenAlex ID(s) of the source(s). Can be a single ID or a list for OR logic.
        **kwargs : dict
            Additional filter parameters.

        Returns
        -------
        Works
            Updated Works object.

        Examples
        --------
        >>> Works().filter_by_source("S137773608")
        >>> Works().filter_by_source(["S137773608", "S202381698"])
        """
        if isinstance(source_id, list):
            # Multiple sources - use OR logic
            id_filter = "|".join(source_id)
            return self.filter(primary_location={"source": {"id": id_filter}}, **kwargs)
        return self.filter(primary_location={"source": {"id": source_id}}, **kwargs)

    def filter_by_topic(self, topic_id, **kwargs):
        """Filter works by primary topic OpenAlex ID.

        Parameters
        ----------
        topic_id : str or list
            OpenAlex ID(s) of the topic(s). Can be a single ID or a list for OR logic.
        **kwargs : dict
            Additional filter parameters.

        Returns
        -------
        Works
            Updated Works object.

        Examples
        --------
        >>> Works().filter_by_topic("T10002")
        >>> Works().filter_by_topic(["T10002", "T10003"])
        """
        if isinstance(topic_id, list):
            # Multiple topics - use OR logic
            id_filter = "|".join(topic_id)
            return self.filter(primary_topic={"id": id_filter}, **kwargs)
        return self.filter(primary_topic={"id": topic_id}, **kwargs)

    def filter_by_subfield(self, subfield_id, **kwargs):
        """Filter works by primary topic subfield OpenAlex ID.

        Parameters
        ----------
        subfield_id : str or list
            OpenAlex ID(s) of the subfield(s). Can be a single ID or a list for OR logic.
        **kwargs : dict
            Additional filter parameters.

        Returns
        -------
        Works
            Updated Works object.

        Examples
        --------
        >>> Works().filter_by_subfield("SF12345")
        >>> Works().filter_by_subfield(["SF12345", "SF67890"])
        """
        if isinstance(subfield_id, list):
            # Multiple subfields - use OR logic
            id_filter = "|".join(subfield_id)
            return self.filter(primary_topic={"subfield": {"id": id_filter}}, **kwargs)
        return self.filter(primary_topic={"subfield": {"id": subfield_id}}, **kwargs)

    def filter_by_funder(self, funder_id, **kwargs):
        """Filter works by funder OpenAlex ID.

        Parameters
        ----------
        funder_id : str or list
            OpenAlex ID(s) of the funder(s). Can be a single ID or a list for OR logic.
        **kwargs : dict
            Additional filter parameters.

        Returns
        -------
        Works
            Updated Works object.

        Examples
        --------
        >>> Works().filter_by_funder("F4320332161")
        >>> Works().filter_by_funder(["F4320332161", "F4320321001"])
        """
        if isinstance(funder_id, list):
            # Multiple funders - use OR logic
            id_filter = "|".join(funder_id)
            return self.filter(grants={"funder": id_filter}, **kwargs)
        return self.filter(grants={"funder": funder_id}, **kwargs)

    def filter_by_award(self, award_id, **kwargs):
        """Filter works by grant award ID.

        Parameters
        ----------
        award_id : str or list
            Grant award ID(s). Can be a single ID or a list for OR logic.
        **kwargs : dict
            Additional filter parameters.

        Returns
        -------
        Works
            Updated Works object.

        Examples
        --------
        >>> Works().filter_by_award("AWARD123")
        >>> Works().filter_by_award(["AWARD123", "AWARD456"])
        """
        if isinstance(award_id, list):
            # Multiple awards - use OR logic
            id_filter = "|".join(award_id)
            return self.filter(grants={"award_id": id_filter}, **kwargs)
        return self.filter(grants={"award_id": award_id}, **kwargs)

    def filter_by_publication_year(
        self, year=None, start_year=None, end_year=None, **kwargs
    ):
        """Filter works by publication year or year range.

        Parameters
        ----------
        year : int, optional
            Exact publication year.
        start_year : int, optional
            Start year for range (inclusive).
        end_year : int, optional
            End year for range (inclusive).
        **kwargs : dict
            Additional filter parameters.

        Returns
        -------
        Works
            Updated Works object.

        Examples
        --------
        >>> Works().filter_by_publication_year(year=2020)
        >>> Works().filter_by_publication_year(start_year=2019, end_year=2021)
        """
        if year is not None:
            return self.filter(publication_year=year, **kwargs)

        if start_year is not None:
            self.filter_gt(publication_year=start_year - 1)
        if end_year is not None:
            self.filter_lt(publication_year=end_year + 1)

        return self.filter(**kwargs)

    def filter_by_publication_date(
        self, date=None, start_date=None, end_date=None, **kwargs
    ):
        """Filter works by publication date or date range.

        Parameters
        ----------
        date : str, optional
            Exact publication date (YYYY-MM-DD format).
        start_date : str, optional
            Start date for range (YYYY-MM-DD format, inclusive).
        end_date : str, optional
            End date for range (YYYY-MM-DD format, inclusive).
        **kwargs : dict
            Additional filter parameters.

        Returns
        -------
        Works
            Updated Works object.

        Examples
        --------
        >>> Works().filter_by_publication_date(date="2020-06-15")
        >>> Works().filter_by_publication_date(start_date="2019-01-01", end_date="2020-12-31")
        """
        if date is not None:
            return self.filter(publication_date=date, **kwargs)

        if start_date is not None:
            self.filter(from_publication_date=start_date)
        if end_date is not None:
            self.filter(to_publication_date=end_date)

        return self.filter(**kwargs)

    def filter_by_type(self, work_type, **kwargs):
        """Filter works by type.

        Parameters
        ----------
        work_type : str
            Type of work (e.g., 'article', 'book', 'dataset').
        **kwargs : dict
            Additional filter parameters.

        Returns
        -------
        Works
            Updated Works object.

        Examples
        --------
        >>> Works().filter_by_type("article")
        >>> Works().filter_by_type("dataset")
        """
        return self.filter(type=work_type, **kwargs)

    def filter_by_cited_by_count(self, min_count=None, max_count=None, **kwargs):
        """Filter works by citation count.

        Parameters
        ----------
        min_count : int, optional
            Minimum citation count.
        max_count : int, optional
            Maximum citation count.
        **kwargs : dict
            Additional filter parameters.

        Returns
        -------
        Works
            Updated Works object.

        Examples
        --------
        >>> Works().filter_by_cited_by_count(min_count=100)
        >>> Works().filter_by_cited_by_count(min_count=10, max_count=100)
        """
        if min_count is not None:
            self.filter_gt(cited_by_count=min_count - 1)
        if max_count is not None:
            self.filter_lt(cited_by_count=max_count + 1)

        return self.filter(**kwargs)

    def filter_by_open_access(self, is_oa=True, oa_status=None, **kwargs):
        """Filter works by open access status.

        Parameters
        ----------
        is_oa : bool, optional
            Whether the work is open access (default: True).
        oa_status : str, optional
            Specific open access status ('gold', 'green', 'hybrid', 'bronze', 'closed').
        **kwargs : dict
            Additional filter parameters.

        Returns
        -------
        Works
            Updated Works object.

        Examples
        --------
        >>> Works().filter_by_open_access(is_oa=True)
        >>> Works().filter_by_open_access(oa_status="gold")
        """
        if oa_status is not None:
            return self.filter(oa_status=oa_status, **kwargs)
        return self.filter(is_oa=is_oa, **kwargs)
