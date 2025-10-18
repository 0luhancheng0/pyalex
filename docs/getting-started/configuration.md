# Configuration

PyAlex supports configuration through environment variables, making it easy to customize behavior per-project or per-environment.

## Environment Variables

### Basic Configuration

Create a `.env` file in your project directory:

```bash
# Your email (recommended for polite pool)
OPENALEX_EMAIL=your.email@example.com

# Optional: API key for authenticated requests
OPENALEX_API_KEY=your_api_key_here
```

### Rate Limiting

```bash
# Requests per second (default: 10)
OPENALEX_RATE_LIMIT=10.0

# Maximum retries for failed requests (default: 3)
OPENALEX_MAX_RETRIES=3

# Backoff factor for retries (default: 0.5)
OPENALEX_BACKOFF_FACTOR=0.5
```

### Timeouts

```bash
# Total timeout in seconds (default: 30)
OPENALEX_TOTAL_TIMEOUT=30.0

# Connection timeout in seconds (default: 10)
OPENALEX_CONNECT_TIMEOUT=10.0
```

### Connection Pooling

```bash
# Maximum total connections (default: 20)
OPENALEX_MAX_CONNECTIONS=20

# Maximum connections per host (default: 10)
OPENALEX_MAX_KEEPALIVE_CONNECTIONS=10
```

### CLI Configuration

```bash
# Batch size for CLI operations (default: 100)
OPENALEX_CLI_BATCH_SIZE=100
```

## Complete `.env` Example

See the [`.env.example`](https://github.com/0luhancheng0/pyalex/blob/main/.env.example) file in the repository for a complete example with all available options.

## Programmatic Configuration

You can also configure PyAlex programmatically:

```python
from pyalex.core.config import config

# View current configuration
print(config['email'])
print(config['rate_limit'])

# Modify configuration (not recommended)
config['rate_limit'] = 5.0
```

!!! warning "Configuration Best Practice"
    Use environment variables instead of modifying config programmatically. This makes your code more portable and easier to deploy.

## Polite Pool vs Authenticated

### Polite Pool (Recommended)

Set your email to get access to the polite pool (faster, more reliable):

```bash
OPENALEX_EMAIL=your.email@example.com
```

Benefits:
- Higher rate limits
- Better reliability
- Priority access

### Authenticated API

For even higher limits, request an API key from OpenAlex:

```bash
OPENALEX_API_KEY=your_api_key
```

Benefits:
- Highest rate limits
- Premium features
- Production-ready

## Rate Limiting

PyAlex respects OpenAlex rate limits:

- **Anonymous**: 10 requests/second, 100,000 requests/day
- **Polite Pool**: 10 requests/second (more reliable)
- **Authenticated**: Higher limits based on your plan

The library automatically handles rate limiting with exponential backoff.

## Next Steps

- [Quick Start Guide](quickstart.md) - Start using PyAlex
- [Basic Usage Guide](../guide/basic-usage.md) - Learn the API
