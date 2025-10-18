# Exceptions

PyAlex defines specific exception types for different error scenarios, making it easier to handle errors appropriately.

## Exception Hierarchy

```
PyAlexException (base)
├── NetworkError
├── APIError
│   └── RateLimitError
├── ValidationError
├── ConfigurationError
├── QueryError
├── DataError
└── CLIError
```

## Exception Classes

::: pyalex.exceptions.PyAlexException
    options:
      show_root_heading: true
      show_source: false

::: pyalex.exceptions.NetworkError
    options:
      show_root_heading: true
      show_source: false

::: pyalex.exceptions.APIError
    options:
      show_root_heading: true
      show_source: false

::: pyalex.exceptions.RateLimitError
    options:
      show_root_heading: true
      show_source: false

::: pyalex.exceptions.ValidationError
    options:
      show_root_heading: true
      show_source: false

::: pyalex.exceptions.ConfigurationError
    options:
      show_root_heading: true
      show_source: false

::: pyalex.exceptions.QueryError
    options:
      show_root_heading: true
      show_source: false

::: pyalex.exceptions.DataError
    options:
      show_root_heading: true
      show_source: false

::: pyalex.exceptions.CLIError
    options:
      show_root_heading: true
      show_source: false

## Usage Examples

### Catching Specific Exceptions

```python
from pyalex import Works
from pyalex.exceptions import RateLimitError, NetworkError, APIError

try:
    results = Works().search("AI").get()
except RateLimitError as e:
    print(f"Rate limited! Retry after: {e.retry_after} seconds")
except NetworkError as e:
    print(f"Network problem: {e.message}")
    print(f"URL: {e.url}")
except APIError as e:
    print(f"API error {e.status_code}: {e.message}")
```

### Handling All PyAlex Exceptions

```python
from pyalex.exceptions import PyAlexException

try:
    results = Works().search("AI").get()
except PyAlexException as e:
    print(f"PyAlex error: {e.message}")
    if e.details:
        print(f"Details: {e.details}")
```

### Validation Errors

```python
from pyalex.exceptions import ValidationError

try:
    # Invalid year format
    works = Works().filter(publication_year="invalid")
except ValidationError as e:
    print(f"Validation failed: {e.message}")
    print(f"Field: {e.field}")
    print(f"Value: {e.value}")
```

### Rate Limiting

```python
import time
from pyalex.exceptions import RateLimitError

def fetch_with_retry(query, max_attempts=3):
    for attempt in range(max_attempts):
        try:
            return query.get()
        except RateLimitError as e:
            if attempt < max_attempts - 1:
                wait_time = e.retry_after or 60
                print(f"Rate limited, waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise
```

## Best Practices

### 1. Catch Specific Exceptions

```python
# Good ✅
try:
    results = Works().search("AI").get()
except RateLimitError:
    # Handle rate limit specifically
    pass
except NetworkError:
    # Handle network issues
    pass

# Bad ❌
try:
    results = Works().search("AI").get()
except Exception:
    # Too broad
    pass
```

### 2. Preserve Exception Chains

```python
# Good ✅
try:
    results = Works().search("AI").get()
except PyAlexException as e:
    raise CustomError("Failed to fetch") from e

# Bad ❌
try:
    results = Works().search("AI").get()
except PyAlexException:
    raise CustomError("Failed to fetch")  # Loses original context
```

### 3. Log Error Details

```python
import logging
from pyalex.exceptions import APIError

logger = logging.getLogger(__name__)

try:
    results = Works().search("AI").get()
except APIError as e:
    logger.error(
        "API error occurred",
        extra={
            "status_code": e.status_code,
            "url": e.url,
            "message": e.message
        }
    )
```

## See Also

- [Troubleshooting Guide](../troubleshooting.md) - Common issues and solutions
- [Configuration](../getting-started/configuration.md) - Error prevention through proper config
- [HTTP Session API](client/httpx_session.md) - Network-level error handling
