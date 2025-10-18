# PyAlex CLI Examples

This guide provides practical examples of using PyAlex from the command line.

## Basic Commands

### Search for Works

```bash
# Simple search
pyalex works --search "machine learning" --limit 10

# Search with filters
pyalex works --search "AI" --publication-year 2023 --limit 20

# Get all results (uses pagination)
pyalex works --search "deep learning" --all

# Save results to JSON
pyalex works --search "neural networks" --limit 100 --json results.json
```

### Filter by Date Range

```bash
# Works from a specific year
pyalex works --publication-year 2023 --limit 50

# Date range (CLI supports year ranges)
pyalex works --search "quantum" --publication-year "2020-2023" --limit 30
```

### Filter by Citations

```bash
# Highly cited works
pyalex works --search "transformer" --cited-by-count "100-" --limit 20

# Recent highly cited works
pyalex works --publication-year 2023 --cited-by-count "50-" --limit 10
```

## Author Commands

### Search for Authors

```bash
# Find authors by name
pyalex authors --search "Geoffrey Hinton" --limit 5

# Get author's works
pyalex authors --search "Yann LeCun" --limit 1

# Filter by institution
pyalex authors --last-known-institution "MIT" --limit 20
```

## Institution Commands

### Search for Institutions

```bash
# Find universities
pyalex institutions --search "Stanford" --limit 5

# Filter by country
pyalex institutions --country-code "US" --limit 20

# Get institution details
pyalex institutions --search "MIT" --limit 1 --json mit.json
```

## Advanced Usage

### Using Batch Operations

```bash
# Process a list of IDs from a file
cat work_ids.txt | pyalex from-ids --json batch_results.json

# Chain commands
pyalex works --search "climate change" --limit 100 --json - | \
  jq '.[] | select(.cited_by_count > 50) | .title'
```

### Combining Filters

```bash
# Complex query
pyalex works \
  --search "artificial intelligence" \
  --publication-year "2022-2023" \
  --cited-by-count "10-" \
  --limit 50 \
  --json ai_recent_cited.json
```

### Display Options

```bash
# Table output (default)
pyalex works --search "python" --limit 10

# JSON output to file
pyalex works --search "python" --limit 10 --json python_works.json

# JSON to stdout (for piping)
pyalex works --search "python" --limit 10 --json -
```

## Configuration

### Using Environment Variables

```bash
# Set your email (recommended for polite pool)
export OPENALEX_EMAIL=your.email@example.com

# Set rate limit
export OPENALEX_RATE_LIMIT=5.0

# Set batch size for bulk operations
export OPENALEX_CLI_BATCH_SIZE=50

# Run command
pyalex works --search "data science" --limit 100
```

### Using .env File

Create a `.env` file in your project:

```bash
OPENALEX_EMAIL=your.email@example.com
OPENALEX_RATE_LIMIT=10.0
OPENALEX_CLI_BATCH_SIZE=100
```

Then run PyAlex commands normally - settings will be loaded automatically!

## Performance Tips

### For Large Datasets

```bash
# Use --all flag for pagination
pyalex works --search "machine learning" --all --json ml_all.json

# Increase batch size for bulk operations
OPENALEX_CLI_BATCH_SIZE=200 pyalex from-ids < large_id_list.txt

# Use --limit to cap results
pyalex works --search "broad query" --limit 1000 --json results.json
```

### Debugging

```bash
# Enable debug mode (verbose output)
pyalex --debug works --search "test" --limit 5

# Test configuration
pyalex --help
```

## Common Use Cases

### 1. Find Recent Papers on a Topic

```bash
pyalex works --search "transformers NLP" \
  --publication-year 2023 \
  --cited-by-count "20-" \
  --limit 50 \
  --json transformers_2023.json
```

### 2. Get Author Bibliography

```bash
# Find author
pyalex authors --search "Andrew Ng" --limit 1 --json author.json

# Extract author ID and get their works
AUTHOR_ID=$(jq -r '.[0].id' author.json)
pyalex works --author "$AUTHOR_ID" --all --json author_works.json
```

### 3. Institution Research Output

```bash
pyalex works --institution "Stanford University" \
  --publication-year 2023 \
  --limit 500 \
  --json stanford_2023.json
```

### 4. Citation Analysis

```bash
# Get highly cited works
pyalex works --search "deep learning" \
  --cited-by-count "500-" \
  --sort cited_by_count:desc \
  --limit 100 \
  --json highly_cited_dl.json

# Analyze with jq
jq '[.[] | {title: .title, citations: .cited_by_count}] | sort_by(.citations) | reverse | .[0:10]' \
  highly_cited_dl.json
```

## Error Handling

```bash
# If rate limited, reduce rate
OPENALEX_RATE_LIMIT=5.0 pyalex works --search "test" --limit 100

# If timeout issues, increase timeout
OPENALEX_TOTAL_TIMEOUT=60.0 pyalex works --search "test" --all

# Check for errors in output
pyalex works --search "test" --limit 10 2>&1 | grep -i error
```

## Tips & Tricks

1. **Use JSON output for processing**: Always use `--json` when you need to process results programmatically

2. **Pipe to jq for filtering**: Combine with `jq` for powerful JSON processing
   ```bash
   pyalex works --search "AI" --limit 100 --json - | jq '.[] | select(.open_access.is_oa == true)'
   ```

3. **Save intermediate results**: For complex workflows, save intermediate results
   ```bash
   pyalex works --search "topic" --limit 1000 --json raw.json
   jq 'map(select(.cited_by_count > 100))' raw.json > filtered.json
   ```

4. **Use environment variables**: Set common config in `.env` to avoid repetition

5. **Batch processing**: For large ID lists, process in batches
   ```bash
   split -l 1000 all_ids.txt batch_
   for batch in batch_*; do
     cat $batch | pyalex from-ids --json "results_$(basename $batch).json"
   done
   ```

## Getting Help

```bash
# General help
pyalex --help

# Command-specific help
pyalex works --help
pyalex authors --help
pyalex institutions --help

# Show version
pyalex --version
```

For more examples, see the Python examples in the `examples/` directory!
