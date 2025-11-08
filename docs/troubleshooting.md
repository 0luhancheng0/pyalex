# Troubleshooting

Common issues and solutions when using PyAlex.

## Installation Issues

### Module Not Found

**Problem**: `ModuleNotFoundError: No module named 'pyalex'`

**Solution**:
```bash
# Ensure PyAlex is installed
pip install pyalex

# Or if using uv
uv pip install pyalex
```

### Import Errors

**Problem**: `ImportError: cannot import name 'Works' from 'pyalex'`

**Solution**: Make sure you're using the latest version:
```bash
pip install --upgrade pyalex
```

## API Errors

### Rate Limit Exceeded

**Problem**: `RateLimitError: Rate limit exceeded`

**Solution**:

1. Reduce request rate:
```bash
# In .env file
OPENALEX_RATE_LIMIT=5.0
```

2. Add your email to access polite pool:
```bash
OPENALEX_EMAIL=your.email@example.com
```

3. Wait before retrying (error message includes retry-after time)

### Network Errors

**Problem**: `NetworkError: Network error: Connection timeout`

**Solution**:

1. Check internet connection
2. Increase timeout:
```bash
OPENALEX_TOTAL_TIMEOUT=60.0
OPENALEX_CONNECT_TIMEOUT=20.0
```

3. Check if OpenAlex is down: [https://status.openalex.org](https://status.openalex.org)

### API Errors

**Problem**: `APIError: HTTP 404 error - Resource not found`

**Solution**:
- Verify the ID format: `W123456789` for works, `A123456789` for authors
- Check if the resource exists in OpenAlex
- Use search instead of direct ID lookup

**Problem**: `APIError: HTTP 500 error - Server error`

**Solution**:
- This is a temporary OpenAlex server issue
- Retry after a few seconds
- Increase retry count:
```bash
OPENALEX_MAX_RETRIES=5
```

## Configuration Issues

### Environment Variables Not Loading

**Problem**: Configuration from `.env` not applied

**Solution**:

1. Ensure `.env` is in project root:
```bash
ls .env  # Should exist
```

2. Check file format:
```bash
# Correct format
OPENALEX_EMAIL=user@example.com

# Incorrect (no spaces, no quotes)
OPENALEX_EMAIL = "user@example.com"
```

3. Install python-dotenv:
```bash
pip install python-dotenv
```

### Configuration Not Taking Effect

**Problem**: Changes to config not working

**Solution**: Restart Python interpreter or CLI session after changing `.env`

## Query Issues

### Validation Errors

**Problem**: `ValidationError: Invalid year format`

**Solution**: Check filter formats:
```python
# Correct
.filter(publication_year=2023)
.filter(publication_year="2020-2023")

# Incorrect
.filter(publication_year="2023-01-01")  # Use publication_date instead
```

### Empty Results

**Problem**: Query returns no results

**Solutions**:

1. Verify filter values:
```python
# Check if filters are too restrictive
results = Works().search("AI").filter(
    publication_year=2023,
    cited_by_count=">1000"  # Maybe too high?
).get()
```

2. Use debug mode:
```bash
pyalex --debug works --search "test" --limit 5
```

3. Check the generated URL:
```python
query = Works().search("test")
print(query.url)
```

### Query Too Slow

**Problem**: Queries taking too long

**Solutions**:

1. Use pagination:
```python
# Instead of fetching all
results = Works().search("AI")[:100]  # Limit to 100
```

2. Use async for parallel queries:
```python
```python
import asyncio
from pyalex import Works

async def fast_query():
    results = await Works().search("AI").get(limit=100)
    return results

asyncio.run(fast_query())
```

3. Increase connection pool:
```bash
OPENALEX_MAX_CONNECTIONS=50
```

## CLI Issues

### Command Not Found

**Problem**: `pyalex: command not found`

**Solution**:

1. Ensure installation completed:
```bash
pip install pyalex
```

2. Check if it's in PATH:
```bash
which pyalex
```

3. Try running as module:
```bash
python -m pyalex works --help
```

### JSON Lines Output Issues

**Problem**: JSONL file not created

**Solution**:

1. Check file path:
```bash
# Relative path
pyalex works --search "AI" --jsonl-file results.jsonl

# Absolute path
pyalex works --search "AI" --jsonl-file /full/path/results.jsonl
```

2. Check permissions:
```bash
# Ensure write permissions
ls -la results.jsonl
```

## Performance Issues

### Slow Pagination

**Problem**: Fetching large datasets is slow

**Solution**:

1. Use cursor pagination for large datasets:
```python
# Better for >10,000 results
results = Works().search("AI").paginate(per_page=200, cursor="*")
```

2. Use async methods:
```python
results = await Works().search("AI").get(limit=1000)
```

### Memory Issues

**Problem**: `MemoryError` when fetching large datasets

**Solution**:

1. Process in batches:
```python
for i in range(0, 10000, 100):
    batch = Works().search("AI")[i:i+100]
    process_batch(batch)
```

2. Use iterator:
```python
for work in Works().search("AI"):
    process_work(work)
    if count >= 1000:
        break
```

## Debugging Tips

### Enable Debug Mode

```bash
# CLI
pyalex --debug works --search "test" --limit 5

# Python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check Version

```python
import pyalex
print(pyalex.__version__)
```

### Inspect Request URLs

```python
query = Works().search("AI").filter(publication_year=2023)
print(query.url)
```

### Test Connection

```python
from pyalex import Works

# Simple test
try:
    result = Works()["W2741809807"]  # Attention Is All You Need paper
    print(f"✅ Connection works! Got: {result['title']}")
except Exception as e:
    print(f"❌ Error: {e}")
```

## Still Having Issues?

1. Check [GitHub Issues](https://github.com/0luhancheng0/pyalex/issues)
2. Search [GitHub Discussions](https://github.com/0luhancheng0/pyalex/discussions)
3. Open a new issue with:
   - PyAlex version
   - Python version
   - Error message and traceback
   - Minimal code to reproduce

## See Also

- [Configuration Guide](getting-started/configuration.md)
- [API Reference](api/exceptions.md)
- [Examples](examples/python.md)
