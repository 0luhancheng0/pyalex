# PyAlex Type Definitions Quick Reference

## Importing Types

```python
from pyalex.typing import Work, Author, Institution, Source, Topic, Publisher, Funder
```

## Core Entity Types

### Work
```python
from pyalex.typing import Work

# Create from dict data (validates at runtime)
work = Work(
    id="https://openalex.org/W2741809807",
    doi="https://doi.org/10.1103/physrevlett.119.156401",
    title="Entanglement measures and their properties",
    display_name="Entanglement measures and their properties",
    publication_year=2017,
    publication_date="2017-10-10",
    type="article",
    cited_by_count=1234,
)

# Access fields with dot notation
print(work.title)  # "Entanglement measures and their properties"
print(work.publication_year)  # 2017
```

### Author
```python
from pyalex.typing import Author

author = Author(
    id="https://openalex.org/A5023888391",
    orcid="https://orcid.org/0000-0002-1234-5678",
    display_name="Albert Einstein",
    works_count=234,
    cited_by_count=45678,
)

# Access fields
print(author.display_name)  # "Albert Einstein"
print(author.works_count)  # 234
```

### Source
```python
from pyalex.typing import Source

source = Source(
    id="https://openalex.org/S123456789",
    issn_l="0028-0836",
    display_name="Nature",
    type="journal",
    is_oa=False,
    works_count=567890,
)
```

### Institution
```python
from pyalex.typing import Institution

institution = Institution(
    id="https://openalex.org/I123456789",
    ror="https://ror.org/012abcd34",
    display_name="University of Example",
    country_code="US",
    type="education",
    works_count=12345,
)
```

### Topic
```python
from pyalex.typing import Topic

topic = Topic(
    id="https://openalex.org/T10001",
    display_name="Quantum Computing",
    description="Research on quantum computers and algorithms",
    keywords=["quantum", "computing", "algorithms"],
    works_count=5678,
)
```

### Publisher  
```python
from pyalex.typing import Publisher

publisher = Publisher(
    id="https://openalex.org/P1234567",
    display_name="Springer Nature",
    hierarchy_level=0,
    lineage=["https://openalex.org/P1234567"],
    works_count=234567,
)
```

### Funder
```python
from pyalex.typing import Funder

funder = Funder(
    id="https://openalex.org/F4320332161",
    display_name="National Science Foundation",
    country_code="US",
    grants_count=12345,
    works_count=234567,
)
```

## Key Nested Types

### Authorship (in Work)
```python
from pyalex.typing import Authorship, DehydratedEntity

authorship = Authorship(
    author=DehydratedEntity(
        id="https://openalex.org/A123456",
        display_name="Jane Smith"
    ),
    author_position="first",
    countries=["US", "UK"],
    is_corresponding=True,
    raw_affiliation_strings=["University of Example, Boston, MA"],
)
```

### Location (in Work)
```python
from pyalex.typing import Location

location = Location(
    is_oa=True,
    landing_page_url="https://doi.org/...",
    pdf_url="https://arxiv.org/pdf/...",
    license="cc-by",
    version="submittedVersion",
)
```

### OpenAccess (in Work)
```python
from pyalex.typing import OpenAccess

open_access = OpenAccess(
    is_oa=True,
    oa_status="gold",
    oa_url="https://...",
    any_repository_has_fulltext=True,
)
```

## Common Patterns

### Safe Field Access
```python
from pyalex.typing import Work

def get_title(work: Work) -> str:
    # Fields are optional, check for None
    return work.title or "Untitled"
```

### Handling Optional Fields
```python
from pyalex.typing import Work

def get_year(work: Work) -> int | None:
    # Direct attribute access
    return work.publication_year
```

### Working with Lists
```python
from pyalex.typing import Work, Authorship

def count_authors(work: Work) -> int:
    authorships: list[Authorship] | None = work.authorships
    return len(authorships) if authorships else 0
```

### Nested Object Access
```python
from pyalex.typing import Author

def get_hindex(author: Author) -> int:
    stats = author.summary_stats
    return stats.h_index if stats else 0
```

### Creating from API Response
```python
from pyalex.typing import Work
from pydantic import ValidationError

# Parse and validate API response
api_response = {...}  # dict from API
try:
    work = Work(**api_response)
    print(work.title)
except ValidationError as e:
    print(f"Invalid data: {e}")
```

### Serialization
```python
from pyalex.typing import Work

work = Work(title="My Paper", publication_year=2024)

# Convert to dict
work_dict = work.model_dump()

# Convert to JSON string
work_json = work.model_dump_json()

# Exclude None values
work_dict_clean = work.model_dump(exclude_none=True)
```

## Type Hints in Functions

```python
from pyalex.typing import Work, Author, Institution

def process_works(works: list[Work]) -> list[str]:
    """Extract titles from a list of works."""
    return [w.title or "Untitled" for w in works]

def analyze_author(author: Author) -> dict[str, int | str]:
    """Extract key author metrics."""
    return {
        "name": author.display_name or "Unknown",
        "works": author.works_count or 0,
        "citations": author.cited_by_count or 0,
    }

def get_institution_country(inst: Institution) -> str | None:
    """Get institution country code."""
    return inst.country_code
```

## Notes

- All models use Pydantic BaseModel with runtime validation
- All fields are optional with `| None` type hints
- Use dot notation for field access: `work.title` instead of `work["title"]`
- Extra fields from API are preserved with `extra="allow"` configuration
- Use `model_dump()` to convert back to dict, `model_dump_json()` for JSON
- ValidationError is raised if data doesn't match expected types

## Full Documentation

See `docs/api/typing.md` for complete documentation and examples.
