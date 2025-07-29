"""Response classes for OpenAlex API."""

import logging

from pyalex.models.base import OpenAlexEntity

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
    """A list of OpenAlexEntity objects with metadata.

    Attributes:
        meta: a dictionary with metadata about the results
        resource_class: the class to use for each entity in the results
        resource_entity_class: optional Pydantic model for validation

    Arguments:
        results: a list of OpenAlexEntity objects
        meta: a dictionary with metadata about the results
        resource_class: the class to use for each entity in the results
        resource_entity_class: optional Pydantic model for validation

    Returns:
        a OpenAlexResponseList object
    """

    def __init__(
        self, 
        results, 
        meta=None, 
        resource_class=OpenAlexEntity, 
        resource_entity_class=None
    ):
        self.resource_class = resource_class
        self.resource_entity_class = resource_entity_class
        self.meta = meta

        # Validate and convert results if entity class is provided
        validated_results = []
        for ent in results:
            if resource_entity_class:
                try:
                    validated_entity = resource_entity_class(**ent)
                    # Convert back to dict for backward compatibility
                    # Use model_dump() with mode='json' to handle datetime serialization
                    validated_dict = validated_entity.model_dump(mode='json')
                    validated_results.append(resource_class(validated_dict))
                except Exception as e:
                    logger.warning(
                        f"Validation failed for {resource_class.__name__}: {e}"
                    )
                    # Fall back to unvalidated dict
                    validated_results.append(resource_class(ent))
            else:
                validated_results.append(resource_class(ent))

        super().__init__(validated_results)
