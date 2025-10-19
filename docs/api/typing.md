# Type Definitions

PyAlex provides comprehensive Pydantic model definitions for all OpenAlex API entities, enabling runtime validation, better type checking, and IDE autocomplete support.

## Installation

The typing module is included with PyAlex by default. Make sure you have Pydantic installed:

```bash
pip install pyalex  # Includes pydantic as a dependency
```

## Basic Usage

Import type definitions from `pyalex.typing`:

```python
from pyalex.typing import Work, Author, Institution

def process_work(work: Work) -> str:
    """Process a work and return its title."""
    title: str | None = work.title
    year: int | None = work.publication_year
    return f"{title} ({year})"

# Create instances with validation
work = Work(id="W123", title="My Paper", publication_year=2024)

# Parse from API response
api_data = {"id": "W123", "title": "My Paper"}
work = Work(**api_data)  # Validates and creates instance
```

## Available Types

### Core Entities

| Type | Description |
|------|-------------|
| `Work` | Scholarly works (papers, books, datasets) |
| `Author` | Authors of scholarly works |
| `Source` | Publication venues (journals, repositories) |
| `Institution` | Research organizations and universities |
| `Topic` | Research topics and subject areas |
| `Publisher` | Publishers of sources |
| `Funder` | Funding organizations |

### Supporting Types

Each entity comes with supporting types for nested objects:

#### Works
- `Authorship` - Author and affiliation information
- `Location` - Where a work is hosted
- `OpenAccess` - Open access status
- `APC` - Article Processing Charges
- `Biblio` - Bibliographic metadata
- `Grant` - Funding information
- `Keyword` - Associated keywords

#### Authors
- `AuthorCounts` - Citation and publication counts
- `AuthorSummaryStats` - h-index, i10-index
- `AuthorLastKnownInstitution` - Affiliation data

#### Sources
- `SourceCounts` - Publication metrics
- `SourceSummaryStats` - Impact metrics
- `APCPrice` - APC pricing

#### Institutions
- `InstitutionGeo` - Geographic location
- `InstitutionCounts` - Metrics
- `InstitutionSummaryStats` - Impact metrics
- `InstitutionRepository` - Hosted repositories

#### Common Types
- `DehydratedEntity` - Minimal entity reference
- `CountsByYear` - Year-by-year counts
- `IDs` - External identifier collection

## Examples

### Type-Safe Work Processing

```python
from pyalex.typing import Work, Authorship

def get_first_author(work: Work) -> str | None:
    """Get the first author's name from a work."""
    authorships: list[Authorship] | None = work.authorships
    if not authorships:
        return None
    
    first_authorship = authorships[0]
    author_info = first_authorship.author
    if author_info:
        return author_info.display_name
    return None

def is_open_access(work: Work) -> bool:
    """Check if a work is open access."""
    open_access = work.open_access
    if open_access:
        return open_access.is_oa or False
    return False
```

### Type-Safe Author Analysis

```python
from pyalex.typing import Author

def get_author_metrics(author: Author) -> dict[str, int]:
    """Extract key metrics from an author."""
    stats = author.summary_stats
    return {
        "works_count": author.works_count or 0,
        "cited_by_count": author.cited_by_count or 0,
        "h_index": stats.h_index if stats else 0,
        "i10_index": stats.i10_index if stats else 0,
    }
```

### Type-Safe Institution Data

```python
from pyalex.typing import Institution

def get_institution_location(institution: Institution) -> str | None:
    """Get institution's location as a formatted string."""
    geo = institution.geo
    if not geo:
        return None
    
    city = geo.city
    country = geo.country
    
    if city and country:
        return f"{city}, {country}"
    return country
```

### Creating and Validating Instances

```python
from pyalex.typing import Work
from pydantic import ValidationError

# Create from dict (validates data)
work_data = {
    "id": "W123456",
    "title": "Machine Learning Fundamentals",
    "publication_year": 2024,
    "cited_by_count": 42
}
work = Work(**work_data)

# Access fields with dot notation
print(work.title)  # "Machine Learning Fundamentals"
print(work.publication_year)  # 2024

# Serialize back to dict
work_dict = work.model_dump()

# Serialize to JSON
work_json = work.model_dump_json()

# Validation errors are caught
try:
    invalid_work = Work(publication_year="not a number")
except ValidationError as e:
    print(f"Validation error: {e}")
```

## IDE Support

With type definitions, modern IDEs provide:

- **Autocomplete**: See available fields as you type
- **Type Checking**: Catch errors before runtime
- **Documentation**: Inline field descriptions
- **Refactoring**: Safe rename and restructure

### VS Code

```json
// settings.json
{
    "python.analysis.typeCheckingMode": "basic"
}
```

### PyCharm

Type hints work automatically with no configuration needed.

## Type Checking with mypy

Add mypy to your project:

```bash
pip install mypy
```

Create a `mypy.ini` configuration:

```ini
[mypy]
python_version = 3.10
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = False
```

Run type checking:

```bash
mypy your_script.py
```

## Important Notes

### Optional Fields

All TypedDict fields use `total=False`, meaning every field is optional. This matches OpenAlex API behavior where different fields may be present depending on the entity and query.

Always use `.get()` with defaults:

```python
# ❌ May raise KeyError
year = work["publication_year"]

# ✓ Safe with None handling  
year = work.get("publication_year")
if year is not None:
    print(f"Published in {year}")
```

### Union Types

Fields that can be `None` use union syntax (`str | None`):

```python
from pyalex.typing import Work

def safe_get_title(work: Work) -> str:
    title: str | None = work.get("title")
    return title if title else "Untitled"
```

### Legacy Fields

Some types include deprecated fields (e.g., `x_concepts`) that may still appear in API responses but should not be used in new code.

## Full Example

See `examples/typing_example.py` for a comprehensive example showing all entity types in use.

## Contributing

To add new types or update existing ones:

1. Edit the relevant file in `pyalex/typing/`
2. Add exports to `pyalex/typing/__init__.py`
3. Update documentation in `docs/api/typing.md`
4. Run formatters: `ruff check --fix pyalex/typing && ruff format pyalex/typing`

## References

- [OpenAlex API Documentation](https://docs.openalex.org/)
- [Python TypedDict Documentation](https://docs.python.org/3/library/typing.html#typing.TypedDict)
- [PEP 589 - TypedDict](https://peps.python.org/pep-0589/)
