---
name: pyalex
description: Interface for querying the OpenAlex academic database using the PyAlex library. Use this skill when you need to search for works, authors, institutions, sources, or funders, or when you need to perform bibliographic analysis.
---

# PyAlex

## Overview

PyAlex is a Python library for interacting with the [OpenAlex API](https://openalex.org/), a comprehensive open catalog of the world's scholarly papers, researchers, journals, and institutions.

Use this skill to:
1.  Search for academic works, authors, and institutions.
2.  Filter results by publication year, citation count, open access status, and more.
3.  Traverse relationships (e.g., finding all works by an author).
4.  Retrieve metadata for bibliometric analysis.

## Core Entities

PyAlex provides classes for the main OpenAlex entities. Import them directly from `pyalex`:

| Class | Represents | OpenAlex ID Prefix |
| :--- | :--- | :--- |
| `Works` | Scientific papers, books, datasets | `W` |
| `Authors` | Researchers and creators | `A` |
| `Institutions` | Universities, companies, agencies | `I` |
| `Sources` | Journals, conferences, repositories | `S` |
| `Funders` | Funding agencies | `F` |
| `Publishers` | Publishing companies | `P` |
| `Topics` | Research topics (clusters of concepts) | `T` |

## Quick Start

### 1. Configuration

Always configure your email to get into the "polite pool" (faster, higher limits).

```python
from pyalex import config
config.email = "your_email@example.com"
# config.api_key = "SECRET_API_KEY" # Optional, for premium access
```

### 2. Basic Search

Use `.search()` for full-text search and `.get()` to retrieve results.

```python
from pyalex import Works

# Search for works containing "quantum computing"
results = Works().search("quantum computing").get(limit=5)

for work in results:
    print(f"{work['id']}: {work['title']}")
```

### 3. Retrieve by ID

Use the item access syntax `Entity()[id]`.

```python
from pyalex import Works

# Get a work by its OpenAlex ID (or DOI)
work = Works()["W2741809807"]
# work = Works()["https://doi.org/10.1234/example"]
print(work["title"])
```

## Filtering & Queries

PyAlex supports chainable methods for building queries.

### Exact Match Filter

Use `.filter(field=value)`.

```python
# Works published in 2023
Works().filter(publication_year=2023).get()

# Works by a specific author
Works().filter(author={"id": "A5023888391"}).get()
```

### Logical Operators

*   **OR**: Pass a list to `.filter()` or use `.filter_or()`.
    *   `filter(field=[val1, val2])`: Matches val1 OR val2.
*   **AND**: Chain `.filter()` calls.
    *   `.filter(year=2023).filter(type="article")`: Matches 2023 AND article.
*   **NOT**: Use `.filter_not()`.
*   **Ranges**: Use `.filter_gt()`, `.filter_lt()`, `.filter_gte()`, `.filter_lte()`.

```python
# Works with > 100 citations AND published after 2020
(Works()
    .filter_gt(cited_by_count=100)
    .filter_gt(publication_year=2020)
    .get())
```

### Available Fields

Common fields for filtering:
*   **Works**: `publication_year`, `type` (article, book-chapter, etc.), `is_oa` (bool), `cited_by_count`.
*   **Authors**: `display_name`, `works_count`, `last_known_institution.id`.
*   **Institutions**: `country_code`, `type` (education, healthcare, etc.).

## Research Workflows

Use these patterns for high-level research tasks.

### 1. Topic Discovery & Literature Review

To find works on a complex topic (e.g., "mechanistic interpretability in transformers"):

**Strategy A: Broad Keyword Search (Start Here)**
Best for initial exploration. Use `search()` which queries titles, abstracts, and fulltext (where available).
```python
results = (Works()
    .search("mechanistic interpretability transformers")
    .filter_gt(publication_year=2020)  # Focus on recent work
    .get())
```

**Strategy B: Concept-Based Search (High Precision)**
OpenAlex tags works with "Concepts" (AI-generated topics).
1.  **Find the Concept**: Search for the concept entity first to get its ID.
2.  **Filter by Concept**: Use the ID to filter works. This captures papers that might miss specific keywords but match the topic.

```python
from pyalex import Concepts, Works

# 1. Find the Concept ID for "Transformer" (the model, not the electrical device)
# Inspect results to find the correct ID (e.g., 'C2779356606')
concepts = Concepts().search("transformer").get()

# 2. Search for works tagged with this concept AND specific keywords
works = (Works()
    .filter(concepts={"id": "C2779356606"})
    .search("mechanistic interpretability")
    .sort(cited_by_count="desc")
    .get())
```

**Strategy C: Title/Abstract Specific Search**
If broad search is too noisy, restrict search to the abstract or title using `.search_filter()`.

```python
# Only matches if "interpretability" is in the title
Works().search_filter(title="interpretability").get()

# Only matches if "transformers" is in the abstract
# Note: abstract searching uses the inverted index.
Works().search_filter(abstract="transformers").get()
```

### 2. Finding "State of the Art" (SOTA)
Combine recency with impact (citation count) to find influential recent papers.

```python
# "Seminal" papers: Highly cited papers from the last 5 years
sota_papers = (Works()
    .filter_gt(publication_year=2019)
    .filter_gt(cited_by_count=50)  # Threshold depends on the field size
    .search("large language models")
    .sort(cited_by_count="desc")
    .get())
```

### 3. Tracking Labs & Authors
Find recent output from a specific researcher or lab.

```python
from pyalex import Authors, Works

# 1. Find Author ID
author = Authors().search("Yann LeCun").get()[0]

# 2. Get their recent works
recent_works = (Works()
    .filter(author={"id": author["id"]})
    .filter_gt(publication_year=2022)
    .sort(publication_year="desc")
    .get())
```

## Pagination

### Getting All Results

For small result sets, `.get()` returns a list. For large sets, iterate over pages.

```python
query = Works().search("generative ai").filter(publication_year=2023)

# Automatic pagination (handled by library)
for work in query.paginate(per_page=200):
    print(work["title"])
```

### Limits

*   `.get(limit=N)`: Fetches up to N results.
*   Default `.get()`: Fetches one page (usually 25 results).

## Advanced Usage

### Selection

Select only specific fields to reduce payload size.

```python
# Only get ID, title, and DOI
Works().select(["id", "title", "doi"]).get()
```

### Sorting

Sort results by a field.

```python
# Newest first
Works().sort(publication_year="desc").get()

# Most cited first
Works().sort(cited_by_count="desc").get()
```

### Grouping (Facets)

Get counts of results grouped by a field.

```python
# Count works by year
counts = Works().search("carbon capture").group_by("publication_year").get()
# Returns: [{'key': '2023', 'count': 150}, {'key': '2022', 'count': 120}, ...]
```

## Best Practices

1.  **Chaining**: Chain methods for readable queries: `Works().search(...).filter(...).sort(...).get()`.
2.  **Context**: Use `with` blocks if you need temporary configuration changes (though usually global config is fine).
3.  **IDs**: OpenAlex IDs often look like `https://openalex.org/W123`. PyAlex handles short IDs (`W123`) and full URLs interchangeably.

## Common Snippets

### Get Result Count (Without Fetching)
Use `.count()` to check the size of a query before downloading.
```python
count = Works().search("climate change").filter(publication_year=2023).count()
print(f"Found {count} works")
```

### Reconstruct Abstract
OpenAlex stores abstracts as "inverted indexes" (word -> [positions]) to save space. PyAlex does **not** automatically reconstruct them by default for raw dicts.

```python
def reconstruct_abstract(inverted_index):
    if not inverted_index: return None
    word_index = []
    for k, v in inverted_index.items():
        for i in v: word_index.append([k, i])
    word_index = sorted(word_index, key=lambda x: x[1])
    return " ".join([x[0] for x in word_index])

work = Works()["W2741809807"]
abstract = reconstruct_abstract(work.get("abstract_inverted_index"))
```

### Filter by Journal (Source)
```python
from pyalex import Sources

# Find works in "Nature"
# 1. Find Source ID
nature_id = Sources().search("Nature").get()[0]["id"]

# 2. Filter
works = Works().filter(primary_location={"source": {"id": nature_id}}).get()
```