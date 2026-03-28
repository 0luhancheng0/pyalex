# Design Spec: Add `--year` option to `expand` command

Add a `--year` (publication year) filter to the `expand` subcommand in the PyAlex CLI to allow users to restrict expanded results to specific timeframes.

## 1. Problem Statement
Currently, the `expand` command allows fetching related entities (works, authors, institutions) but does not provide a way to filter the resulting works by their publication year. Users frequently need to "expand" a set of authors or works but only care about the output from a specific period (e.g., "get all works by these authors published in 2017-2018").

## 2. Proposed Changes

### 2.1. Shared Year Filtering Helper
Extract the year-filtering logic from `pyalex/cli/commands/works.py` into a reusable helper function in `pyalex/cli/commands/utils.py`.

**New Helper**: `apply_publication_year_filter(query, publication_year: str)`
- **Input**: `BaseOpenAlex` query object, `publication_year` string (e.g., "2020", "2017:2018").
- **Behavior**:
    - Parses the year string (handles single years and ranges).
    - Applies `query.filter_by_publication_year(year=...)` or `query.filter_by_publication_year(start_year=..., end_year=...)`.
    - Raises `typer.Exit(1)` with a clear error message on invalid formats.
- **Refactor**: Update `pyalex/cli/commands/works.py` to use this helper to ensure consistency.

### 2.2. Update `expand` Command Signature
Add the `--year` option to `pyalex/cli/commands/expand.py`:

```python
publication_year: Annotated[
    Optional[str],
    typer.Option(
        "--year",
        help="Filter by publication year (e.g. '2020' or range '2019:2021'). Only applies to modes returning Works.",
        rich_help_panel=METADATA_PANEL, # Add to metadata panel if exists
    ),
] = None,
```

### 2.3. Update `expand` Logic

#### Validation
If `publication_year` is provided and the `mode` does not return `Works` (e.g., `work_author`, `work_institution`, `author_institution`), print a warning to `stderr` and ignore the filter.

#### Query Modes (`author_work`, `work_forward`, `topic_work`)
These modes already use a `Works()` query. Simply call the new helper:
1. Initialize `query = Works()`.
2. Apply IDs via `add_id_list_option_to_command`.
3. Apply year filter via `apply_publication_year_filter(query, publication_year)`.
4. If `limit` is set, ensure sorting by `cited_by_count:desc` (this is already standard for these modes).

#### ID-collection Modes (`work_related`, `work_backward`)
If `publication_year` is **NOT** provided:
- Maintain current behavior: local frequency-based sampling → batch retrieval.

If `publication_year` **IS** provided:
- **Approach A (Approved)**:
    1. Collect **ALL** unique Work IDs from the input file (no local sampling).
    2. Initialize `query = Works()`.
    3. Apply collected IDs via `add_id_list_option_to_command(query, id_string, "openalex_id", Works)`.
    4. Apply year filter via `apply_publication_year_filter(query, publication_year)`.
    5. If `limit` is provided:
        - Apply `query.sort(cited_by_count="desc")`.
    6. Execute using `handle_large_id_list_if_needed` (handles batching, limits, and output).

## 3. Error Handling
- **Malformed Year**: "202x" or "2017-2018" (invalid separator) will result in a descriptive error message and exit.
- **Empty Results**: If the year filter removes all results, standard PyAlex "No results found" message will be shown.

## 4. Testing Strategy
- **Unit Test**: Verify `apply_publication_year_filter` correctly parses valid formats and rejects invalid ones.
- **Integration Test**:
    - Run `pyalex expand --mode author_work -i <mock_authors> --year "2017:2018"`.
    - Verify output JSONL contains only works with `publication_year` in `[2017, 2018]`.
    - Test edge cases: single year (`--year 2020`), open ranges if supported (`--year 2020:`).

## 5. Documentation
- Update `expand` command's help text to mention `--year`.
- Update docstrings where appropriate.
