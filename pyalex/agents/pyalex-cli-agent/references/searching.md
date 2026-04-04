# Searching & Filtering with PyAlex CLI

Use this reference when discovery or filtering is required.

## Core Command Pattern
`pyalex [entity] --search "[query]" [filters] [sorting]`

- **Entities**: `works`, `authors`, `institutions`, `funders`, `topics`, `sources`, `publishers`, `domains`, `fields`, `subfields`, `keywords`.

## Filter Cheat Sheet (Works)
- `--year "2020:2023"`: Range.
- `--cited-by-count ">100"`: Citation threshold.
- `--type "article"`: Work type.
- `--author-ids "A123,A456"`: Works by specific authors.
- `--oa-status "gold"`: Open access status.
- `--is-oa`: Boolean filter.

## Sorting & Pagination
- `--sort-by "cited_by_count:desc"`: Most cited first.
- `--sort-by "publication_date:desc"`: Newest first.
- `--limit 10`: Number of results.
- `--all`: Retrieve all (use with caution/JSONL).

## Examples
- `pyalex works --search "transformer" --year 2023 --sort-by "cited_by_count:desc" --limit 5`
- `pyalex authors --search "Yann LeCun"`
