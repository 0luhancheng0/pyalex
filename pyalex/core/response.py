"""Response classes for OpenAlex API."""

import logging

try:
    from pyalex.logger import get_logger

    logger = get_logger()
except ImportError:
    # Fallback if logging module is not available
    logger = logging.getLogger(__name__)


class QueryError(ValueError):
    """Exception raised for errors in the query."""

    pass


class OpenAlexResponseList(list):
    """A list of dictionary objects with metadata.

    Attributes:
        meta: a dictionary with metadata about the results
        resource_class: the class to use for each entity in the results

    Arguments:
        results: a list of dictionary objects
        meta: a dictionary with metadata about the results
        resource_class: the class to use for each entity in the results

    Returns:
        a OpenAlexResponseList object
    """

    def __init__(
        self,
        results,
        meta=None,
        resource_class=dict,
        resource_entity_class=None,  # Kept for backward compatibility but ignored
    ):
        self.resource_class = resource_class
        self.meta = meta

        # Convert results to specified resource class
        converted_results = []
        for ent in results:
            converted_results.append(resource_class(ent))

        super().__init__(converted_results)

    def to_dataframe(self):
        """Convert the response list to a pandas DataFrame.

        Returns
        -------
        pd.DataFrame
            DataFrame with all results and metadata stored as attributes.
        """
        try:
            import pandas as pd
        except ImportError:
            raise ImportError(
                "pandas is required to convert results to DataFrame. "
                "Install it with: pip install pandas"
            )

        # Convert list of dicts to DataFrame
        df = pd.DataFrame(list(self))

        # Store metadata as DataFrame attributes
        if self.meta:
            df.attrs["meta"] = self.meta

        return df
