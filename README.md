# PyAlex: Command Line Interface for OpenAlex

This is a forked and enhanced version of the [PyAlex](https://github.com/J535D165/pyalex) library with two major improvements:

1. **Comprehensive Command Line Interface (CLI)**
2. **Asynchronous Request Handling**

## 🚀 Installation

```bash
pip install pyalex
```

## 📖 Overview

PyAlex provides a powerful command-line interface to interact with the [OpenAlex](https://openalex.org/) database, which contains comprehensive bibliographic data on scholarly works, authors, institutions, and more.

### Key Features

- **Rich CLI Commands**: Search and filter works, authors, institutions, funders, and other entities
- **Flexible Output**: Export results to JSON, display in tables, or pipe to other tools
- **Advanced Filtering**: Support for date ranges, citation counts, institutional affiliations, and more
- **Batch Processing**: Handle large datasets efficiently with async processing
- **Grouping & Aggregation**: Group results by various fields for analysis
- **Pagination Control**: Retrieve specific pages or all results

## 🛠️ CLI Reference

```
> pyalex --help
                                                                                                                                                                                      
 Usage: pyalex [OPTIONS] COMMAND [ARGS]...                                                                                                                                            
                                                                                                                                                                                      
 CLI interface for the OpenAlex database                                                                                                                                              
                                                                                                                                                                                      
                                                                                                                                                                                      
╭─ Options ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --debug               -d               Enable debug output including API URLs and internal details                                                                                 │
│ --dry-run                              Print a list of queries that would be run without executing them                                                                            │
│ --batch-size                  INTEGER  Batch size for requests with multiple IDs (default: 100) [default: 100]                                                                     │
│ --install-completion                   Install completion for the current shell.                                                                                                   │
│ --show-completion                      Show completion for the current shell, to copy it or customize the installation.                                                            │
│ --help                                 Show this message and exit.                                                                                                                 │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ works          Search and retrieve works from OpenAlex.                                                                                                                            │
│ authors        Search and retrieve authors from OpenAlex.                                                                                                                          │
│ institutions   Search and retrieve institutions from OpenAlex.                                                                                                                     │
│ funders        Search and retrieve funders from OpenAlex.                                                                                                                          │
│ from-ids       Retrieve entities by their OpenAlex IDs from stdin.                                                                                                                 │
│ show           Display a JSON file containing OpenAlex data in table format.                                                                                                       │
│ topics         Search and retrieve topics from OpenAlex                                                                                                                            │
│ sources        Search and retrieve sources (journals/venues) from OpenAlex                                                                                                         │
│ publishers     Search and retrieve publishers from OpenAlex                                                                                                                        │
│ domains        Search and retrieve domains from OpenAlex                                                                                                                           │
│ fields         Search and retrieve fields from OpenAlex                                                                                                                            │
│ subfields      Search and retrieve subfields from OpenAlex                                                                                                                         │
│ keywords       Search and retrieve keywords from OpenAlex                                                                                                                          │
╰──────────────────────────────────────────────────────────────
```

## 📚 Quick Start Examples

### Basic Searches

```bash
# Search for works about machine learning
pyalex works --search "machine learning" --limit 10

# Find authors at MIT
pyalex authors --search "MIT" --limit 5

# Search for institutions in Australia
pyalex institutions --search "Australia" --limit 10

# Look up funders
pyalex funders --search "National Science Foundation"
```

### Export to JSON

```bash
# Save COVID-19 research to file
pyalex works --search "COVID-19" --year "2020:2022" --json covid_research.json

# Export all works by specific authors
pyalex works --author-ids "A1234567890,A0987654321" --all --json author_works.json
```

### Advanced Filtering

```bash
# Find highly cited papers from 2020-2022
pyalex works --year "2020:2022" --sort-by "cited_by_count:desc" --limit 100

# Get works by publication date range
pyalex works --date "2023-01-01:2023-12-31" --type "article"

# Find works by multiple authors (OR logic)
pyalex works --author-ids "A123,A456,A789" --all
```

### Grouping and Analysis

```bash
# Group works by publication year
pyalex works --search "artificial intelligence" --group-by "publication_year"

# Analyze open access status distribution
pyalex works --search "climate change" --group-by "oa_status"

# Group by work type
pyalex works --author-ids "A1234567890" --group-by "type"
```

## 🔗 Asynchronous Processing

The library includes async support for improved performance when making multiple requests or handling large datasets:

```python
import asyncio
from pyalex import Works

async def fetch_works():
    works = Works().search("machine learning").filter(publication_year=2023)
    async for work in works:
        print(work['title'])

asyncio.run(fetch_works())
```

## 🤝 Contributing

This project builds upon the excellent work of the original [PyAlex](https://github.com/J535D165/pyalex) library. Contributions are welcome!

## 📄 License

MIT License - see the [LICENSE](LICENSE) file for details.