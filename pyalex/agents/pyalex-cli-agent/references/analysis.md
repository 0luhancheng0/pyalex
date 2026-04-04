# Bibliometric Analysis & Grouping

Use this reference for aggregating data and understanding distributions.

## Grouping Logic
The `--group-by` parameter can be used with any entity search.

- **Command**: `pyalex [entity] [filters] --group-by [field]`

## Common Grouping Targets (Works)
- `publication_year`: Number of works per year.
- `oa_status`: Distribution of open access types.
- `type`: Distribution of work types (article, book, etc.).
- `institutions.id`: Works grouped by institution.

## Examples
- `pyalex works --search "GPT-4" --group-by "publication_year"`
- `pyalex works --author-ids "A5023888364" --group-by "oa_status"`
