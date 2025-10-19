# API and CLI Feature Parity

PyAlex now provides **full feature parity** between the API and CLI interfaces! All filtering capabilities available in the CLI are now accessible through convenient API methods.

## Overview

Previously, many advanced filtering options were only available through the CLI (e.g., `--institution-ids`, `--year`, `--type`), requiring users to work directly with low-level filter methods when using the Python API. Now, both interfaces provide the same high-level convenience methods.

## New Convenience Methods

### Works Class

The `Works` class now provides the following convenience methods:

#### Filter by Entity IDs

```python
from pyalex import Works

# Filter by author ID(s)
works = Works().filter_by_author('A2208157607')
works = Works().filter_by_author(['A2208157607', 'A5023888391'])  # Multiple authors (OR logic)

# Filter by institution ID(s)
works = Works().filter_by_institution('I97018004')
works = Works().filter_by_institution(['I97018004', 'I27837315'])  # Multiple institutions (OR logic)

# Filter by source/journal ID(s)
works = Works().filter_by_source('S137773608')

# Filter by topic ID(s)
works = Works().filter_by_topic('T10002')

# Filter by subfield ID(s)
works = Works().filter_by_subfield('SF12345')

# Filter by funder ID(s)
works = Works().filter_by_funder('F4320332161')

# Filter by grant award ID(s)
works = Works().filter_by_award('AWARD123')
```

#### Filter by Publication Date/Year

```python
# Filter by exact year
works = Works().filter_by_publication_year(year=2020)

# Filter by year range
works = Works().filter_by_publication_year(start_year=2020, end_year=2021)

# Filter by exact date
works = Works().filter_by_publication_date(date='2020-06-15')

# Filter by date range
works = Works().filter_by_publication_date(
    start_date='2020-01-01',
    end_date='2020-12-31'
)
```

#### Filter by Work Attributes

```python
# Filter by work type
works = Works().filter_by_type('article')

# Filter by citation count
works = Works().filter_by_cited_by_count(min_count=100, max_count=1000)
works = Works().filter_by_cited_by_count(min_count=100)  # At least 100 citations

# Filter by open access status
works = Works().filter_by_open_access(is_oa=True)
works = Works().filter_by_open_access(oa_status='gold')
```

#### Chaining Filters

All methods can be chained together for complex queries:

```python
works = (Works()
    .filter_by_institution('I97018004')
    .filter_by_publication_year(start_year=2020, end_year=2023)
    .filter_by_type('article')
    .filter_by_cited_by_count(min_count=50)
    .search('machine learning'))

# Execute the query
import asyncio
results = asyncio.run(works.get(per_page=10))
```

### Other Entity Classes

Convenience methods are also available for other entity types:

#### Authors

```python
from pyalex import Authors

# Filter by affiliation
authors = Authors().filter_by_affiliation('I97018004')

# Filter by works count
authors = Authors().filter_by_works_count(min_count=50, max_count=200)

# Filter by citation count
authors = Authors().filter_by_cited_by_count(min_count=1000)

# Filter by h-index
authors = Authors().filter_by_h_index(min_h=20)

# Filter by ORCID
authors = Authors().filter_by_orcid('0000-0001-2345-6789')
```

#### Institutions

```python
from pyalex import Institutions

# Filter by country
institutions = Institutions().filter_by_country('US')

# Filter by type
institutions = Institutions().filter_by_type('education')

# Filter by location
institutions = Institutions().filter_by_location(city='Boston', region='Massachusetts')

# Filter by Global South status
institutions = Institutions().filter_by_is_global_south(True)

# Filter by works count
institutions = Institutions().filter_by_works_count(min_count=10000)
```

#### Funders

```python
from pyalex import Funders

# Filter by country
funders = Funders().filter_by_country('US')

# Filter by works count
funders = Funders().filter_by_works_count(min_count=1000)

# Filter by citation count
funders = Funders().filter_by_cited_by_count(min_count=10000)
```

#### Sources

```python
from pyalex import Sources

# Filter by type
sources = Sources().filter_by_type('journal')

# Filter by publisher
sources = Sources().filter_by_publisher('P4310319900')

# Filter by ISSN
sources = Sources().filter_by_issn('0028-0836')

# Filter by open access status
sources = Sources().filter_by_is_oa(True)
```

#### Topics

```python
from pyalex import Topics

# Filter by field
topics = Topics().filter_by_field('F100')

# Filter by subfield
topics = Topics().filter_by_subfield('SF12345')

# Filter by domain
topics = Topics().filter_by_domain('D100')
```

## API ↔ CLI Equivalence

Here's how API methods map to CLI options:

| API Method | CLI Option | Example |
|------------|------------|---------|
| `.filter_by_author()` | `--author-ids` | `--author-ids "A123"` |
| `.filter_by_institution()` | `--institution-ids` | `--institution-ids "I123"` |
| `.filter_by_topic()` | `--topic-ids` | `--topic-ids "T123"` |
| `.filter_by_funder()` | `--funder-ids` | `--funder-ids "F123"` |
| `.filter_by_publication_year()` | `--year` | `--year "2020:2021"` |
| `.filter_by_publication_date()` | `--date` | `--date "2020-01-01:2020-12-31"` |
| `.filter_by_type()` | `--type` | `--type "article"` |

### Example Comparison

**CLI:**
```bash
pyalex works --institution-ids "I97018004" --year "2020:2021" --type "article" --search "AI" --limit 10
```

**API:**
```python
from pyalex import Works
import asyncio

works = (Works()
    .filter_by_institution('I97018004')
    .filter_by_publication_year(start_year=2020, end_year=2021)
    .filter_by_type('article')
    .search('AI'))

results = asyncio.run(works.get(per_page=10))
```

Both produce identical queries to the OpenAlex API!

## Benefits

✅ **Consistency** - Same features available in both interfaces  
✅ **Discoverability** - Convenience methods are easier to find than raw filter syntax  
✅ **Type Safety** - Method signatures provide clear parameter types  
✅ **Documentation** - Each method has detailed docstrings with examples  
✅ **Chainability** - Methods can be chained for readable, complex queries  
✅ **Maintainability** - Both CLI and API use the same underlying implementation  

## Migration Guide

If you were using low-level filters before, here's how to migrate:

### Before (Low-level filters)

```python
# Old way - using raw filters
works = Works().filter(authorships={"institutions": {"id": "I97018004"}})
works = Works().filter_gt(publication_year=2019).filter_lt(publication_year=2022)
```

### After (Convenience methods)

```python
# New way - using convenience methods
works = Works().filter_by_institution('I97018004')
works = Works().filter_by_publication_year(start_year=2020, end_year=2021)
```

The new methods are clearer, more concise, and match CLI usage patterns!

## See Also

- [Basic Usage Examples](../examples/basic_usage.py)
- [API/CLI Parity Examples](../examples/api_cli_parity.py)
- [CLI Examples](../examples/CLI_EXAMPLES.md)
