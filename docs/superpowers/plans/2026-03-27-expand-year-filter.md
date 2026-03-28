# Add `--year` option to `expand` command Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `--year` option to the `expand` command to filter results by publication year.

**Architecture:** 
1. Extract year filtering logic into a reusable helper in `pyalex/cli/commands/utils.py`.
2. Refactor `pyalex/cli/commands/works.py` to use this helper.
3. Update `pyalex/cli/commands/expand.py` to include the `--year` option and apply it to `Works` queries.
4. For ID-collection modes, switch to API-side filtering and citation-based sampling when a year is provided.

**Tech Stack:** Python, Typer, PyAlex (httpx/asyncio).

---

### Task 1: Create Year Filtering Helper

**Files:**
- Modify: `pyalex/cli/commands/utils.py`
- Test: `tests/test_cli_utils.py`

- [ ] **Step 1: Write unit tests for the helper**

```python
# Add to tests/test_cli_utils.py
from pyalex import Works
from pyalex.cli.commands.utils import apply_publication_year_filter
import pytest

def test_apply_publication_year_filter_single_year():
    query = Works()
    query = apply_publication_year_filter(query, "2020")
    assert "publication_year:2020" in query.url

def test_apply_publication_year_filter_range():
    query = Works()
    query = apply_publication_year_filter(query, "2017:2018")
    assert "publication_year:>2016" in query.url
    assert "publication_year:<2019" in query.url

def test_apply_publication_year_filter_invalid():
    query = Works()
    with pytest.raises(SystemExit):
        apply_publication_year_filter(query, "invalid")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_cli_utils.py -v`
Expected: FAIL (ImportError or AttributeError for `apply_publication_year_filter`)

- [ ] **Step 3: Implement the helper in `pyalex/cli/commands/utils.py`**

```python
# Add to pyalex/cli/commands/utils.py
def apply_publication_year_filter(query, publication_year: str):
    """Apply publication year filter to a query object."""
    import typer
    if ":" in publication_year:
        try:
            start_year, end_year = publication_year.split(":")
            s_year = int(start_year.strip()) if start_year.strip() else None
            e_year = int(end_year.strip()) if end_year.strip() else None
            query = query.filter_by_publication_year(
                start_year=s_year, end_year=e_year
            )
        except ValueError:
            typer.echo(
                "Error: Invalid year range format. Use 'start:end' "
                "(e.g., '2019:2020')",
                err=True,
            )
            raise typer.Exit(1) from None
    else:
        try:
            year = int(publication_year.strip())
            query = query.filter_by_publication_year(year=year)
        except ValueError:
            typer.echo(
                "Error: Invalid year format. Use a single year or range "
                "(e.g., '2020' or '2019:2020')",
                err=True,
            )
            raise typer.Exit(1) from None
    return query
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_cli_utils.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyalex/cli/commands/utils.py tests/test_cli_utils.py
git commit -m "feat: add apply_publication_year_filter helper"
```

---

### Task 2: Refactor `works` command to use the helper

**Files:**
- Modify: `pyalex/cli/commands/works.py`

- [ ] **Step 1: Replace inline logic with helper call**

```python
# In pyalex/cli/commands/works.py
# Remove existing publication_year parsing logic and replace with:
from .utils import apply_publication_year_filter

# ... inside works function ...
if publication_year:
    query = apply_publication_year_filter(query, publication_year)
```

- [ ] **Step 2: Run existing works tests to ensure no regression**

Run: `pytest tests/test_cli.py -k works -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add pyalex/cli/commands/works.py
git commit -m "refactor: use apply_publication_year_filter in works command"
```

---

### Task 3: Update `expand` command signature and validation

**Files:**
- Modify: `pyalex/cli/commands/expand.py`

- [ ] **Step 1: Add `--year` option and validation logic**

```python
# In pyalex/cli/commands/expand.py
from .help_panels import OUTPUT_PANEL # Ensure METADATA_PANEL or similar is used if available

# Add to expand function arguments:
    publication_year: Annotated[
        Optional[str],
        typer.Option(
            "--year",
            help="Filter by publication year (e.g. '2020' or range '2019:2021'). Only applies to modes returning Works.",
        ),
    ] = None,

# Add validation at start of expand function:
    if publication_year and mode not in {
        ExpandMode.author_work,
        ExpandMode.work_forward,
        ExpandMode.work_related,
        ExpandMode.work_backward,
        ExpandMode.topic_work,
    }:
        typer.echo(
            f"Warning: --year is only used in modes returning Works (not {mode.value}); ignored.",
            err=True,
        )
```

- [ ] **Step 2: Verify help text shows the new option**

Run: `pyalex expand --help`
Expected: `--year` option is visible in the help output.

- [ ] **Step 3: Commit**

```bash
git add pyalex/cli/commands/expand.py
git commit -m "feat: add --year option to expand command signature"
```

---

### Task 4: Implement year filtering for `expand` query modes

**Files:**
- Modify: `pyalex/cli/commands/expand.py`

- [ ] **Step 1: Apply year filter to `author_work`, `work_forward`, and `topic_work`**

```python
# In pyalex/cli/commands/expand.py
from .utils import apply_publication_year_filter

# Update ExpandMode.work_forward block:
        if mode == ExpandMode.work_forward:
            query = Works()
            # ... existing ID logic ...
            if publication_year:
                query = apply_publication_year_filter(query, publication_year)
            # ... rest of block ...

# Update ExpandMode.author_work block:
        elif mode == ExpandMode.author_work:
            query = Works()
            # ... existing ID logic ...
            if publication_year:
                query = apply_publication_year_filter(query, publication_year)
            # ... rest of block ...

# Update ExpandMode.topic_work block:
        elif mode == ExpandMode.topic_work:
            query = Works()
            # ... existing ID logic ...
            if publication_year:
                query = apply_publication_year_filter(query, publication_year)
            # ... rest of block ...
```

- [ ] **Step 2: Commit**

```bash
git add pyalex/cli/commands/expand.py
git commit -m "feat: apply year filter to expand query modes"
```

---

### Task 5: Implement year filtering for `expand` ID-collection modes

**Files:**
- Modify: `pyalex/cli/commands/expand.py`

- [ ] **Step 1: Update `work_backward` and `work_related` logic**

```python
# In pyalex/cli/commands/expand.py

# ... in the execution section ...
        else:
            # work_backward and work_related
            if publication_year:
                query = Works()
                id_string = ",".join(formatted_ids)
                # Use openalex_id filter for direct ID matches
                from ..batch import add_id_list_option_to_command
                query = add_id_list_option_to_command(query, id_string, "openalex_id", Works)
                query = apply_publication_year_filter(query, publication_year)
                
                if effective_limit is not None:
                    query = query.sort(cited_by_count="desc")

                results = handle_large_id_list_if_needed(
                    query,
                    Works,
                    effective_limit is None,
                    effective_limit,
                    effective_jsonl_path,
                    normalize=normalize,
                )

                if results is None:
                    results = execute_standard_query(
                        query, "Works",
                        all_results=effective_limit is None,
                        limit=effective_limit,
                    )
                    _output_results(results, jsonl_path=effective_jsonl_path, normalize=normalize)
            else:
                # Existing behavior: direct batch retrieval by ID
                results = asyncio.run(
                    _async_retrieve_entities(Works, formatted_ids, "Works")
                )
                _output_results(
                    results,
                    jsonl_path=effective_jsonl_path,
                    normalize=normalize,
                )
```

- [ ] **Step 2: Commit**

```bash
git add pyalex/cli/commands/expand.py
git commit -m "feat: apply year filter to expand ID-collection modes"
```

---

### Task 6: Final Verification

**Files:**
- Create: `tests/test_expand_year.py`

- [ ] **Step 1: Write integration tests for `expand --year`**

```python
# Create tests/test_expand_year.py
import json
import subprocess
import os

def test_expand_author_work_year_filter():
    # Use a known author ID and year range
    # Note: Requires network or mock. Assuming environment supports live tests or mocks are in place.
    # For a robust plan, we use a small input file.
    with open("temp_authors.jsonl", "w") as f:
        f.write(json.dumps({"id": "https://openalex.org/A5023888391"}) + "\n")
    
    try:
        cmd = [
            "python", "-m", "pyalex", "expand", 
            "--mode", "author_work", 
            "-i", "temp_authors.jsonl", 
            "--year", "2017:2018",
            "--jsonl"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        lines = result.stdout.strip().split("\n")
        assert len(lines) > 0
        for line in lines:
            if not line.strip(): continue
            data = json.loads(line)
            year = data.get("publication_year")
            assert 2017 <= year <= 2018
    finally:
        if os.path.exists("temp_authors.jsonl"):
            os.remove("temp_authors.jsonl")

def test_expand_work_related_year_filter():
    with open("temp_works.jsonl", "w") as f:
        f.write(json.dumps({"id": "https://openalex.org/W2741809807"}) + "\n")
    
    try:
        cmd = [
            "python", "-m", "pyalex", "expand", 
            "--mode", "work_related", 
            "-i", "temp_works.jsonl", 
            "--year", "2020",
            "--jsonl"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        lines = result.stdout.strip().split("\n")
        if lines and lines[0]:
            for line in lines:
                data = json.loads(line)
                assert data.get("publication_year") == 2020
    finally:
        if os.path.exists("temp_works.jsonl"):
            os.remove("temp_works.jsonl")
```

- [ ] **Step 2: Run verification tests**

Run: `pytest tests/test_expand_year.py -v`
Expected: PASS

- [ ] **Step 3: Cleanup and Final Commit**

```bash
git add tests/test_expand_year.py
git commit -m "test: add integration tests for expand --year filter"
```
