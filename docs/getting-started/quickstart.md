# Quick Start

Get started with PyAlex in minutes!

## Installation

```bash
pip install pyalex
```

## Your First Query

```python
from pyalex import Works

# Search for works about machine learning
works = Works().search("machine learning")

# Get first 10 results
results = works[:10]

for work in results:
    print(f"{work['title']} - {work['cited_by_count']} citations")
```

## Basic Concepts

### Entities

PyAlex provides access to several OpenAlex entities:

```python
from pyalex import Works, Authors, Institutions, Sources, Topics, Funders

# Search works
works = Works().search("quantum computing")

# Search authors
authors = Authors().search("Einstein")

# Search institutions
institutions = Institutions().search("MIT")
```

### Filtering

Add filters to refine your search:

```python
# Filter by year
works = Works().search("AI").filter(publication_year=2023)

# Filter by citation count
works = Works().search("AI").filter(cited_by_count=">100")

# Multiple filters
works = Works().search("AI").filter(
    publication_year=2023,
    cited_by_count=">50",
    type="article"
)
```

### Pagination

```python
# Get specific range
first_50 = Works().search("AI")[0:50]
next_50 = Works().search("AI")[50:100]

# Iterate through all results
for work in Works().search("AI"):
    print(work['title'])
    if some_condition:
        break
```

## Async Usage

For better performance with large datasets:

```python
import asyncio
from pyalex import Works

async def fetch_works():
    results = await Works().search("AI").get(limit=100)
    return results

# Run async function
results = asyncio.run(fetch_works())
```

## Command-Line Interface

PyAlex includes a powerful CLI:

```bash
# Search for works
pyalex works --search "machine learning" --limit 10

# Filter by year
pyalex works --search "AI" --year 2023 --limit 20

# Export to JSON Lines
pyalex works --search "quantum" --limit 100 --jsonl-file results.jsonl

# Get help
pyalex --help
pyalex works --help
```

## Configuration

Create a `.env` file for persistent configuration:

```bash
OPENALEX_EMAIL=your.email@example.com
OPENALEX_RATE_LIMIT=10.0
```

## Common Patterns

### Get Work by ID

```python
# Using OpenAlex ID
work = Works()["W2741809807"]
print(work['title'])
```

### Filter by Author

```python
# Find author first
author = Authors().search("Albert Einstein")[0]

# Get their works
works = Works().filter(author=author['id'])
```

### Citation Count Range

```python
# Highly cited papers
highly_cited = Works().search("AI").filter(
    cited_by_count="100-1000"
)

# Papers with 50+ citations
popular = Works().search("AI").filter(
    cited_by_count=">50"
)
```

### Date Ranges

```python
# Year range
recent = Works().search("AI").filter(
    publication_year="2020-2023"
)

# Specific date range
dated = Works().search("AI").filter(
    publication_date="2023-01-01:2023-12-31"
)
```

## Next Steps

- **[User Guide](../guide/basic-usage.md)** - Learn advanced features
- **[CLI Guide](../guide/cli-usage.md)** - Master the command-line interface
- **[API Reference](../api/entities/works.md)** - Complete API documentation
- **[Examples](../examples/python.md)** - More code examples

## Need Help?

- Check the [Troubleshooting Guide](../troubleshooting.md)
- See [Configuration Guide](configuration.md)
- Browse [Examples](../examples/python.md)
