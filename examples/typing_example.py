"""Example demonstrating the use of PyAlex typing module.

This example shows how to use Pydantic models from pyalex.typing to improve
code quality, enable IDE autocomplete, and validate data at runtime.
"""

from pydantic import ValidationError

from pyalex.typing import Author
from pyalex.typing import Authorship
from pyalex.typing import Funder
from pyalex.typing import Institution
from pyalex.typing import Publisher
from pyalex.typing import Source
from pyalex.typing import Topic
from pyalex.typing import Work


def get_work_title(work: Work) -> str:
    """Extract the title from a work.

    Args:
        work: A Work entity from the OpenAlex API

    Returns:
        The work's title, or "Untitled" if not available
    """
    return work.title or "Untitled"


def get_publication_year(work: Work) -> int | None:
    """Extract the publication year from a work.

    Args:
        work: A Work entity from the OpenAlex API

    Returns:
        The publication year, or None if not available
    """
    return work.publication_year


def get_first_author(work: Work) -> str | None:
    """Get the first author's name from a work.

    Args:
        work: A Work entity from the OpenAlex API

    Returns:
        The first author's display name, or None if no authors
    """
    authorships: list[Authorship] | None = work.authorships
    if not authorships:
        return None

    first_authorship = authorships[0]
    author_info = first_authorship.author
    if author_info:
        return author_info.display_name
    return None


def count_institutions(work: Work) -> int:
    """Count the number of distinct institutions in a work's authorships.

    Args:
        work: A Work entity from the OpenAlex API

    Returns:
        Number of distinct institutions
    """
    return work.institutions_distinct_count or 0


def is_open_access(work: Work) -> bool:
    """Check if a work is open access.

    Args:
        work: A Work entity from the OpenAlex API

    Returns:
        True if the work is open access
    """
    open_access = work.open_access
    if open_access:
        return open_access.is_oa or False
    return False


def get_author_hindex(author: Author) -> int | None:
    """Get an author's h-index.

    Args:
        author: An Author entity from the OpenAlex API

    Returns:
        The author's h-index, or None if not available
    """
    stats = author.summary_stats
    if stats:
        return stats.h_index
    return None


def get_source_issn(source: Source) -> str | None:
    """Get the ISSN-L for a source.

    Args:
        source: A Source entity from the OpenAlex API

    Returns:
        The source's ISSN-L, or None if not available
    """
    return source.issn_l


def get_institution_country(institution: Institution) -> str | None:
    """Get an institution's country code.

    Args:
        institution: An Institution entity from the OpenAlex API

    Returns:
        The institution's country code, or None if not available
    """
    return institution.country_code


def get_topic_keywords(topic: Topic) -> list[str]:
    """Get keywords associated with a topic.

    Args:
        topic: A Topic entity from the OpenAlex API

    Returns:
        List of keywords
    """
    return topic.keywords or []


def get_publisher_lineage(publisher: Publisher) -> list[str]:
    """Get the lineage of a publisher.

    Args:
        publisher: A Publisher entity from the OpenAlex API

    Returns:
        List of publisher IDs in the hierarchy
    """
    return publisher.lineage or []


def get_funder_grants_count(funder: Funder) -> int:
    """Get the number of grants from a funder.

    Args:
        funder: A Funder entity from the OpenAlex API

    Returns:
        Number of grants
    """
    return funder.grants_count or 0


def analyze_work_metrics(work: Work) -> dict[str, int | str | bool]:
    """Analyze various metrics for a work.

    Args:
        work: A Work entity from the OpenAlex API

    Returns:
        Dictionary with various metrics
    """
    return {
        "title": get_work_title(work),
        "year": get_publication_year(work) or 0,
        "citations": work.cited_by_count or 0,
        "authors": len(work.authorships or []),
        "is_oa": is_open_access(work),
    }


def create_work_from_api_response(api_data: dict) -> Work | None:
    """Create a Work instance from API response data with validation.

    Args:
        api_data: Dictionary from OpenAlex API response

    Returns:
        Validated Work instance, or None if validation fails
    """
    try:
        work = Work(**api_data)
        return work
    except ValidationError as e:
        print(f"Validation error: {e}")
        return None


def serialize_work(work: Work) -> dict:
    """Convert a Work instance back to a dictionary.

    Args:
        work: A Work entity

    Returns:
        Dictionary representation of the work
    """
    # Exclude None values for cleaner output
    return work.model_dump(exclude_none=True)


if __name__ == "__main__":
    # Example: Create a work from dict data with validation
    work_data = {
        "id": "https://openalex.org/W1234567890",
        "title": "Example Research Paper",
        "publication_year": 2024,
        "cited_by_count": 42,
    }

    work = Work(**work_data)
    print(f"Title: {work.title}")
    print(f"Year: {work.publication_year}")
    print(f"Citations: {work.cited_by_count}")

    # Convert back to dict
    work_dict = work.model_dump()
    print(f"\nSerialized: {work_dict}")

    print("\nPyAlex typing examples - see function definitions above")
