# PyAlex Documentation

Welcome to PyAlex, a comprehensive Python interface to the [OpenAlex](https://openalex.org/) database!

## What is PyAlex?

PyAlex is a powerful Python library and command-line tool for accessing and analyzing scholarly data from OpenAlex, one of the world's largest open bibliographic databases. PyAlex provides:

- **🚀 Fast async HTTP/2 client** - Built on httpx for optimal performance
- **🎯 Intuitive Python API** - Simple, pythonic interface for complex queries
- **💻 Rich CLI** - Powerful command-line interface with JSON export
- **📊 Comprehensive coverage** - Works, authors, institutions, sources, topics, and more
- **🔧 Flexible filtering** - Advanced query building with logical operators
- **📦 Batch processing** - Efficient handling of large datasets
- **⚙️ Configurable** - Environment-based configuration with `.env` support

## Quick Example

```python
import asyncio
from pyalex import Works

async def main():
    # Find AI research from 2023
    results = await Works().search("artificial intelligence").filter(
        publication_year=2023
    ).get(limit=10)

## Features at a Glance

### Python API
- Async-first design for better performance
- Intuitive query building with method chaining
- Support for all OpenAlex entities (Works, Authors, Institutions, etc.)
- Advanced filtering with OR/NOT/range operators
- Automatic pagination and cursor support

### Command-Line Interface
- Search and filter from the terminal
- Export results to JSON
- Batch processing with progress bars
- Group-by and aggregation support
- Pipe-friendly output formats

### Configuration
- Environment variable support with `.env` files
- Configurable rate limiting and timeouts
- API key authentication
- Comprehensive error handling

## Getting Started

<div class="grid cards" markdown>

- :material-clock-fast:{ .lg .middle } **Quick Start**

    ---

    Get up and running in minutes

    [:octicons-arrow-right-24: Quick Start Guide](getting-started/quickstart.md)

- :material-book-open-page-variant:{ .lg .middle } **User Guide**

    ---

    Learn about filtering, pagination, and batch operations

    [:octicons-arrow-right-24: Read the Guide](guide/basic-usage.md)

- :material-api:{ .lg .middle } **API Reference**

    ---

    Complete API documentation for all modules

    [:octicons-arrow-right-24: API Reference](api/entities/works.md)

- :material-console:{ .lg .middle } **CLI Usage**

    ---

    Master the command-line interface

    [:octicons-arrow-right-24: CLI Guide](guide/cli-usage.md)

</div>

## Why PyAlex?

### Modern Architecture
- **Async-only**: No synchronous fallbacks that degrade performance
- **HTTP/2**: Faster connections with multiplexing
- **Modular**: Clean separation of concerns, easy to maintain

### Developer Friendly
- **Type hints**: Full type annotations for better IDE support
- **Rich errors**: Specific exception types with helpful messages
- **Extensive examples**: 6+ working examples covering common use cases
- **CLI helpers**: Formatted output, progress bars, dry-run mode

### Production Ready
- **Rate limiting**: Built-in respect for API limits
- **Retry logic**: Exponential backoff with jitter
- **Connection pooling**: Efficient resource usage
- **Error handling**: Graceful degradation and informative errors

## Support

- **Issues**: [GitHub Issues](https://github.com/0luhancheng0/pyalex/issues)
- **Discussions**: [GitHub Discussions](https://github.com/0luhancheng0/pyalex/discussions)
- **OpenAlex Docs**: [OpenAlex API Documentation](https://docs.openalex.org/)

## License

PyAlex is released under the [MIT License](https://github.com/0luhancheng0/pyalex/blob/main/LICENSE).

## Acknowledgments

PyAlex builds upon the excellent work of the original [PyAlex library](https://github.com/J535D165/pyalex) by J535D165, with significant enhancements for async-first operation, improved modularity, and comprehensive CLI support.

The [OpenAlex](https://openalex.org/) database is maintained by OurResearch and provides open access to scholarly metadata.
