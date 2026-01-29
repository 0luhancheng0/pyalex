# PyAlex Typing Module

This module provides Pydantic model definitions for all OpenAlex API entities, enabling runtime validation, better type checking, and IDE autocomplete support when working with PyAlex data.

## Usage

```python
from pyalex.typing import Work, Author, Institution

# Type hints for function parameters and return values
def process_work(work: Work) -> str:
    """Process a work and return its title."""
    return work.title or "Untitled"

def get_author_name(author: Author) -> str:
    """Extract author display name."""
    return author.display_name or "Unknown"

# Creating instances with validation
work = Work(id="W123", title="My Paper", publication_year=2024)
author = Author(id="A456", display_name="Jane Doe", works_count=42)

# Parse from API response dict
work_data = {"id": "W123", "title": "My Paper", "publication_year": 2024}
work = Work(**work_data)  # Validates and creates Work instance
```

## Available Types

### Core Entities
- `Work` - Scholarly works (papers, books, datasets, etc.)
- `Author` - Authors of works
- `Source` - Publication venues (journals, repositories, etc.)
- `Institution` - Research organizations and universities
- `Topic` - Research topics and subject areas
- `Publisher` - Publishers of sources
- `Funder` - Funding organizations

### Supporting Types

#### Works
- `Authorship` - Author and affiliation information
- `Location` - Where a work is hosted
- `OpenAccess` - Open access status
- `APC` - Article Processing Charges
- `Biblio` - Bibliographic info (volume, issue, pages)
- `Grant` - Funding information
- `Keyword` - Keywords associated with works

#### Authors
- `AuthorCounts` - Citation and publication counts
- `AuthorSummaryStats` - h-index, i10-index
- `AuthorLastKnownInstitution` - Affiliation information

#### Sources
- `SourceCounts` - Citation and publication counts
- `SourceSummaryStats` - Impact metrics
- `APCPrice` - APC pricing information

#### Institutions
- `InstitutionGeo` - Geographic location data
- `InstitutionCounts` - Publication metrics
- `InstitutionSummaryStats` - Impact metrics
- `InstitutionRepository` - Hosted repositories

#### Topics
- `TopicDomain` - Broad research domain
- `TopicField` - Research field
- `TopicSubfield` - Research subfield
- `TopicSiblings` - Related topics

#### Publishers
- `PublisherCounts` - Publication metrics
- `PublisherSummaryStats` - Impact metrics

#### Funders
- `FunderCounts` - Funding metrics
- `FunderSummaryStats` - Impact metrics

#### Common Types
- `DehydratedEntity` - Minimal entity reference (id + display_name)
- `CountsByYear` - Year-by-year counts
- `IDs` - External identifier collection
- `InternationalDisplay` - Multilingual names
- `Geo` - Geographic coordinates
- `SummaryStats` - Common statistics

## Notes

### Pydantic Models
All entity types are Pydantic BaseModel subclasses with `extra="allow"` configuration. This means:
- All fields are optional (can be `None`)
- Runtime validation is performed when creating instances
- Extra fields from the API are preserved
- You get `.dict()` and `.json()` methods for serialization

### Field Access
With Pydantic models, you can access fields using dot notation:

```python
# Pydantic model access (preferred)
title = work.title  # Returns None if not set
year = work.publication_year

# Also supports dict-style access for compatibility
title = work.get("title", "Untitled")
```

### Legacy Fields
Some types include legacy fields like `x_concepts` which are deprecated in the OpenAlex API but may still appear in responses.

### Dynamic Fields
Some nested structures use generic dict types where the exact structure is complex or varies. Pydantic's `extra="allow"` configuration preserves these fields even if not explicitly defined.

## Type Checking and Validation

Pydantic provides runtime validation:

```python
from pyalex.typing import Work

# Valid data
work = Work(id="W123", title="My Paper")  # ✓ Creates Work instance

# Invalid data raises ValidationError
work = Work(publication_year="not a number")  # ✗ ValidationError

# Parse from API response
api_response = {"id": "W123", "title": "Paper", "publication_year": 2024}
work = Work(**api_response)  # ✓ Validates and creates instance

# Serialize back to dict/json
work_dict = work.model_dump()  # Pydantic v2
work_json = work.model_dump_json()  # Pydantic v2
```

## Contributing

When the OpenAlex API adds new fields or entities:

1. Update the relevant TypedDict in `pyalex/typing/`
2. Add the new type to `__init__.py` exports
3. Update this README with the new types
4. Run `ruff check --fix pyalex/typing && ruff format pyalex/typing`

## References

- [OpenAlex API Documentation](https://docs.openalex.org/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Pydantic V2 Migration Guide](https://docs.pydantic.dev/latest/migration/)
