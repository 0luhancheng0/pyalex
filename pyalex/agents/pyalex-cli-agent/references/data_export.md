# Data Export & Bulk Retrieval

Use this reference for bulk processing, ID resolution, and exporting to files.

## Bulk Processing from IDs
The `from-ids` command accepts OpenAlex IDs, DOIs, or PMIDs from stdin.

- **Example**: `echo "https://doi.org/10.1038/s41586-020-2169-x" | pyalex from-ids`
- **Example**: `cat doi_list.txt | pyalex from-ids --jsonl-file results.jsonl`

## Export Formats
- `--jsonl-file output.jsonl`: Preferred for large datasets.
- `--limit`: Limits the number of exported items.
- `--all`: Export entire result set.

## Visualization
The `show` command displays JSON/JSONL data in a formatted table.

- **Example**: `pyalex show results.jsonl`
