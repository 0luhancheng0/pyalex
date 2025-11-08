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
- **Embeddings Visualization**: Interactive visualization of research embeddings with Embedding Atlas
- **LLM Integration**: Model Context Protocol server exposing PyAlex queries as agent tools

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

## �️ Textual TUI

Prefer a keyboard-driven experience? Launch the Textual interface and explore OpenAlex data with live tables, detail panes, and keyboard shortcuts:

```bash
pyalex-tui
```

Key bindings:

- `Ctrl+C` – Quit
- `F5` – Refresh the current query
- `d` – Toggle the detail panel

The left sidebar lets you pick the entity type (works/authors), set the query and limit, and provide optional `select` fields. Results appear in the main table; select a row to inspect full JSON in the detail panel.

## 🤖 MCP Server

Integrate PyAlex with Model Context Protocol-compatible agents by running the bundled server:

```bash
pyalex-mcp  # defaults to stdio transport
```

Tools currently exposed:

- `search_works(query?, limit=25, select?, filters?, sort?)`
- `search_authors(query?, limit=25, select?, filters?, sort?)`

Each tool accepts optional filters (mapping of field names to values) and respects OpenAlex rate limits. See the [MCP documentation](https://modelcontextprotocol.io/) for instructions on wiring the server into your agent runtime.

## �📚 Examples & Documentation

### Python API Examples

Check out the `examples/` directory for comprehensive Python usage examples:

- **basic_usage.py** - Simple queries and fundamental operations
- **advanced_filtering.py** - Complex filters and combinations
- **pagination_examples.py** - Efficient handling of large result sets
- **batch_operations.py** - Processing multiple items efficiently
- **async_usage.py** - Async patterns for better performance
- **streamlit_example.py** - Interactive Streamlit app with Embedding Atlas

Run any example:
```bash
cd examples
python basic_usage.py
# Or run the Streamlit app
streamlit run streamlit_example.py
```

### Embeddings Visualization

PyAlex includes integration with [Embedding Atlas](https://apple.github.io/embedding-atlas/) for interactive visualization of research embeddings in Streamlit apps:

```python
from pyalex import Works
from pyalex.embeddings import prepare_works_for_embeddings, pyalex_embedding_atlas

# Fetch and prepare data
works = Works().search("machine learning").get(limit=1000)
prepared = prepare_works_for_embeddings(works, text_column="abstract")

# Create interactive visualization
selection = pyalex_embedding_atlas(prepared, show_table=True)
```

See `pyalex/embeddings/README.md` and `docs/embeddings.md` for full documentation.

### CLI Examples

See `examples/CLI_EXAMPLES.md` for detailed command-line usage patterns including:
- Searching and filtering
- Export and batch processing
- Configuration via environment variables
- Performance optimization tips

### Configuration

PyAlex supports configuration via environment variables. Create a `.env` file in your project:

```bash
# Your email (recommended for polite pool access)
OPENALEX_EMAIL=your.email@example.com

# Optional: API key for authenticated requests
OPENALEX_API_KEY=your_api_key_here

# Rate limiting (requests per second)
OPENALEX_RATE_LIMIT=10.0

# Batch size for CLI operations
OPENALEX_CLI_BATCH_SIZE=100
```

See `.env.example` for all available configuration options.

## 🔗 Asynchronous Processing

PyAlex is now **async-only** for better performance. All HTTP requests use `httpx` with HTTP/2 support:

```python
```python
import asyncio
from pyalex import Works

async def fetch_works():
    # Get AI research from 2023 with >100 citations
    results = await Works().search("artificial intelligence").filter(
        publication_year=2023,
        cited_by_count=">100"
    ).get(limit=100)
```

See `examples/async_usage.py` for more async patterns.

## 🤝 Contributing

This project builds upon the excellent work of the original [PyAlex](https://github.com/J535D165/pyalex) library. Contributions are welcome!

## 📄 License

MIT License - see the [LICENSE](LICENSE) file for details.