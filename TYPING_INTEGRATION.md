# Typing Integration in PyAlex

## Overview

PyAlex now includes comprehensive Pydantic-based type definitions for all OpenAlex entities. These type hints are integrated throughout the codebase to provide better IDE support, static type checking, and runtime validation capabilities.

## What Was Integrated

### 1. Entity Classes (pyalex/entities/)

All entity classes now have TYPE_CHECKING imports from the typing module:

- `Work` - Works entity with full type support
- `Author` - Authors entity
- `Source` - Sources/journals entity
- `Institution` - Institutions entity
- `Topic` - Topics entity
- `Publisher` - Publishers entity
- `Funder` - Funders entity

### 2. Utility Functions (pyalex/utils.py)

The `from_id()` function now has proper return type hints:

```python
def from_id(
    openalex_id: str,
) -> Work | Author | Source | Institution | Topic | Publisher | Funder | dict | None:
    """Get an OpenAlex entity from its ID with automatic type detection."""
```

### 3. CLI Formatters (pyalex/cli/formatters.py)

Formatter classes now have TYPE_CHECKING imports for better type hints on methods that process entity dictionaries.

## Usage

### For Static Type Checking

The typing hints are available for static type checkers like mypy and IDE autocomplete:

```python
from pyalex.entities import Work

def process_work(work: Work) -> str:
    """Process a work entity."""
    return work.get("title", "Untitled")
```

### For Runtime Validation

You can also use the Pydantic models directly for runtime validation:

```python
from pyalex.typing import Work
from pydantic import ValidationError

# Validate and parse API response
api_response = {"id": "W123", "title": "My Paper", "publication_year": 2024}
try:
    work = Work(**api_response)
    print(work.title)  # Access with dot notation
    print(work.publication_year)
except ValidationError as e:
    print(f"Invalid data: {e}")
```

### Type Checking Without Runtime Overhead

The `TYPE_CHECKING` pattern is used throughout to avoid circular imports and runtime overhead:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyalex.typing import Work as WorkType
```

This means:
- Type checkers see and use the type hints
- No runtime import overhead
- No circular dependency issues

## Benefits

### 1. Better IDE Support

- Autocomplete for entity fields
- Type hints show expected structure
- Inline documentation

### 2. Static Type Checking

- Catch type errors before runtime
- Ensure correct API usage
- Better refactoring support

### 3. Optional Runtime Validation

- Use Pydantic models when validation is needed
- Use entity classes (dict subclasses) for performance
- Choose the right tool for the job

## Important Notes

### No Runtime Validation by Default

The integration does NOT add runtime validation to existing API calls. Entity classes remain as lightweight `dict` subclasses. This preserves:

- Performance characteristics
- Backward compatibility
- Existing behavior

### When to Use Each Approach

**Use entity classes (Work, Author, etc.) when:**
- Making API calls with PyAlex
- Performance is critical
- You trust the API response format

**Use Pydantic models (from pyalex.typing) when:**
- You need runtime validation
- You want to validate user input
- You need serialization/deserialization
- You're building types from scratch

## Examples

### Example 1: Type Hints for Function Parameters

```python
from pyalex.entities import Work, Author

def get_work_authors(work: Work) -> list[str]:
    """Extract author names from a work."""
    authorships = work.get("authorships", [])
    return [
        a.get("author", {}).get("display_name", "Unknown")
        for a in authorships
    ]

def get_author_metrics(author: Author) -> dict[str, int]:
    """Extract metrics from an author."""
    return {
        "works": author.get("works_count", 0),
        "citations": author.get("cited_by_count", 0),
    }
```

### Example 2: Using from_id() with Type Hints

```python
from pyalex.utils import from_id

# Type checkers know this returns a Work | Author | Source | ... | None
entity = from_id("W123456789")

# Type narrowing with isinstance
if isinstance(entity, dict) and "publication_year" in entity:
    # This is likely a Work
    print(f"Work from {entity.get('publication_year')}")
```

### Example 3: Runtime Validation with Pydantic

```python
from pyalex.typing import Work, Authorship
from pydantic import ValidationError

# Validate complex nested structures
try:
    work = Work(
        id="W123",
        title="My Paper",
        publication_year=2024,
        authorships=[
            Authorship(
                author={"id": "A456", "display_name": "Jane Doe"},
                author_position="first"
            )
        ]
    )
    
    # Serialize to dict or JSON
    work_dict = work.model_dump()
    work_json = work.model_dump_json()
    
except ValidationError as e:
    print(f"Validation failed: {e}")
```

## Migration Guide

### No Changes Required

Existing code continues to work without modifications. The type hints are purely additive and don't change runtime behavior.

### Optional: Add Type Hints to Your Code

You can gradually add type hints to your own code:

```python
# Before
def analyze_works(works):
    for work in works:
        print(work.get("title"))

# After
from pyalex.entities import Work

def analyze_works(works: list[Work]) -> None:
    for work in works:
        print(work.get("title"))
```

### Optional: Use Pydantic Models

For new code that needs validation:

```python
from pyalex.typing import Work

def validate_and_process(data: dict) -> Work:
    """Validate data and return a Work model."""
    return Work(**data)  # Raises ValidationError if invalid
```

## Documentation

For full Pydantic model documentation, see:
- `pyalex/typing/README.md` - Module overview
- `pyalex/typing/QUICKREF.md` - Quick reference
- `docs/api/typing.md` - Full API documentation
- `examples/typing_example.py` - Usage examples
