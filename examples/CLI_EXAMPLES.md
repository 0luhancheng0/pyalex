# PyAlex CLI Examples

This guide provides practical examples of using PyAlex from the command line.

## Basic Commands

### Search for Works

```bash
# Simple search
pyalex works --search "machine learning" --limit 10

# Search with filters
pyalex works --search "AI" --year 2023 --limit 20

# Get all results (uses pagination)
pyalex works --search "deep learning" --all

# Save results to JSON Lines
pyalex works --search "neural networks" --limit 100 --jsonl-file results.jsonl
```

### Filter by Date Range

```bash
# Works from a specific year
pyalex works --year 2023 --limit 50

# Date range (CLI supports year ranges)
pyalex works --search "quantum" --year "2020:2023" --limit 30
```

### Filter by Citations

```bash
# Highly cited works
pyalex works --search "transformer" --cited-by-count "100:" --limit 20

# Recent highly cited works
pyalex works --year 2023 --cited-by-count "50:" --limit 10
```

### Citation and Venue Filters

```bash
# Works that cite a given OpenAlex work ID
pyalex works --cites "W2741809807" --limit 10

# Works that are cited by a specific work
pyalex works --cited-by "W2147561236" --limit 10

# Filter by venue metadata
pyalex works --source-issn "2167-8359" --limit 20
pyalex works --source-host-org-ids "P4310320104" --limit 20
pyalex works --host-venue-ids "S1983995261" --limit 20
```

### Open Access and Fulltext Filters

```bash
# Gold open access works
pyalex works --oa-status gold --limit 20

# Require any OA plus fulltext and search abstracts
pyalex works --is-oa --has-fulltext \
  --abstract-search "graphene oxide" --limit 20

# Works that have been retracted
pyalex works --is-retracted --limit 20

# Explicitly request closed-access items without fulltext
pyalex works --not-oa --no-fulltext --limit 10
```

## Author Commands

### Search for Authors

```bash
# Find authors by name
pyalex authors --search "Geoffrey Hinton" --limit 5

# Get author's works
pyalex authors --search "Yann LeCun" --limit 1

# Filter by affiliated institution OpenAlex ID
pyalex authors --institution-ids "I136200762" --limit 20

# Filter by institution ROR
pyalex authors --institution-rors "https://ror.org/01an7q238" --limit 20
```

### Presence Flags

```bash
# Require authors with ORCID and Twitter profiles
pyalex authors --has-orcid --has-twitter --limit 20

# Exclude authors with Wikipedia pages
pyalex authors --no-wikipedia --limit 20
```

## Concept Commands

```bash
# Explore concept taxonomy
pyalex concepts --search "computer vision" --limit 20

# Retrieve all concepts grouped by level
pyalex concepts --group-by level --limit 200
```

## Institution Commands

### Search for Institutions

```bash
# Find universities
pyalex institutions --search "Stanford" --limit 5

# Filter by country
pyalex institutions --country-code "US" --limit 20

# Get institution details
pyalex institutions --search "MIT" --limit 1 --jsonl-file mit.jsonl
```

## Advanced Usage

### Using Batch Operations

```bash
# Process a list of IDs from a file
cat work_ids.txt | pyalex from-ids --jsonl-file batch_results.jsonl

# Chain commands
pyalex works --search "climate change" --limit 100 --jsonl | \
  jq 'select(.cited_by_count > 50) | .title'
```

### Combining Filters

```bash
# Complex query
pyalex works \
  --search "artificial intelligence" \
  --year "2022:2023" \
  --cited-by-count "10-" \
  --limit 50 \
  --jsonl-file ai_recent_cited.jsonl
```

### Display Options

```bash
# Table output (default)
pyalex works --search "python" --limit 10

# JSON Lines output to file
pyalex works --search "python" --limit 10 --jsonl-file python_works.jsonl

# JSON Lines to stdout (for piping)
pyalex works --search "python" --limit 10 --jsonl
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
pyalex works --search "machine learning" --all --jsonl-file ml_all.jsonl

# Increase batch size for bulk operations
OPENALEX_CLI_BATCH_SIZE=200 pyalex from-ids < large_id_list.txt

# Use --limit to cap results
pyalex works --search "broad query" --limit 1000 --jsonl-file results.jsonl
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
  --year 2023 \
  --cited-by-count "20-" \
  --limit 50 \
  --jsonl-file transformers_2023.jsonl
```

### 2. Get Author Bibliography

```bash
# Find author
pyalex authors --search "Andrew Ng" --limit 1 --jsonl-file author.jsonl

# Extract author ID and get their works
AUTHOR_ID=$(jq -r '.id' author.jsonl)
pyalex works --author "$AUTHOR_ID" --all --jsonl-file author_works.jsonl
```

### 3. Institution Research Output

```bash
pyalex works --institution "Stanford University" \
  --year 2023 \
  --limit 500 \
  --jsonl-file stanford_2023.jsonl
```

### 4. Citation Analysis

```bash
# Get highly cited works
pyalex works --search "deep learning" \
  --cited-by-count "500-" \
  --sort cited_by_count:desc \
  --limit 100 \
  --jsonl-file highly_cited_dl.jsonl

# Analyze with jq
jq -s '[.[] | {title: .title, citations: .cited_by_count}] | sort_by(.citations) | reverse | .[0:10]' \
  highly_cited_dl.jsonl
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
