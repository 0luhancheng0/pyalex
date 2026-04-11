# PyAlex CLI Agent Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a modular, scenario-based Gemini CLI skill to empower an AI agent to autonomously use the PyAlex CLI for scholarly research.

**Architecture:** A main `SKILL.md` routing agent tasks to one of three specialized reference files for searching, data export, or analysis.

**Tech Stack:** PyAlex CLI, Gemini CLI Skill System.

---

### Task 1: Initialize Skill Directory and Main Router

**Files:**
- Create: `pyalex/agents/pyalex-cli-agent/SKILL.md`

- [ ] **Step 1: Write the main router `SKILL.md`**

```markdown
---
name: pyalex-cli-agent
description: Use the pyalex CLI to search, filter, retrieve, and analyze OpenAlex scholarly data. Trigger when the user asks for scholarly works, authors, institutions, funders, topics, or bibliometric data. This skill should be used whenever the agent needs to autonomously find or collect information from the OpenAlex database.
---

# PyAlex CLI Agent Router

You are a scholarly research expert using the PyAlex CLI. Your goal is to autonomously find, retrieve, and analyze scholarly data from OpenAlex.

## Routing Logic
1. **Searching & Filtering**: If the task involves finding works, authors, or entities by specific criteria (e.g., "Find papers on X", "Who are the top authors in Y?"), read `references/searching.md`.
2. **Data Export & Retrieval**: If the task involves downloading metadata, handling lists of IDs (DOIs/PMIDs), or exporting to files (e.g., "Save these DOIs to JSONL"), read `references/data_export.md`.
3. **Analysis & Grouping**: If the task involves grouping, counts, or frequency analysis (e.g., "What's the OA status distribution?", "Group by year"), read `references/analysis.md`.

## Quick Reference
- Always use `--limit` (default: 25) to avoid huge result sets unless requested.
- Use `--jsonl-file <filename>` for large downloads to avoid terminal buffer issues.
- Use `--dry-run` to verify complex filters before execution.
- If a command is missing, try prefixing with `uv run pyalex`.
```

- [ ] **Step 2: Commit initial skill structure**

```bash
git add pyalex/agents/pyalex-cli-agent/SKILL.md
git commit -m "feat: add pyalex-cli-agent skill router"
```

---

### Task 2: Implement Searching Reference File

**Files:**
- Create: `pyalex/agents/pyalex-cli-agent/references/searching.md`

- [ ] **Step 1: Write `searching.md` with syntax for discovery**

```markdown
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
```

- [ ] **Step 2: Commit search reference**

```bash
git add pyalex/agents/pyalex-cli-agent/references/searching.md
git commit -m "feat: add searching reference to pyalex-cli-agent skill"
```

---

### Task 3: Implement Data Export Reference File

**Files:**
- Create: `pyalex/agents/pyalex-cli-agent/references/data_export.md`

- [ ] **Step 1: Write `data_export.md` with syntax for bulk retrieval**

```markdown
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
```

- [ ] **Step 2: Commit export reference**

```bash
git add pyalex/agents/pyalex-cli-agent/references/data_export.md
git commit -m "feat: add data export reference to pyalex-cli-agent skill"
```

---

### Task 4: Implement Analysis Reference File

**Files:**
- Create: `pyalex/agents/pyalex-cli-agent/references/analysis.md`

- [ ] **Step 1: Write `analysis.md` for grouping and distributions**

```markdown
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
```

- [ ] **Step 2: Commit analysis reference**

```bash
git add pyalex/agents/pyalex-cli-agent/references/analysis.md
git commit -m "feat: add analysis reference to pyalex-cli-agent skill"
```

---

### Task 5: Create Initial Evaluation Test Cases

**Files:**
- Create: `pyalex/agents/pyalex-cli-agent/evals/evals.json`

- [ ] **Step 1: Write initial test prompts**

```json
{
  "skill_name": "pyalex-cli-agent",
  "evals": [
    {
      "id": 0,
      "prompt": "Find the 5 most cited papers about 'reinforcement learning' published in 2023.",
      "expected_output": "The agent should construct a 'pyalex works' command with filters for search query, year 2023, sort by cited_by_count, and limit 5.",
      "files": []
    },
    {
      "id": 1,
      "prompt": "What is the distribution of open access status for works by author A5000000000?",
      "expected_output": "The agent should construct a 'pyalex works' command with --author-ids A5000000000 and --group-by oa_status.",
      "files": []
    },
    {
      "id": 2,
      "prompt": "Take the DOI '10.1038/s41586-020-2169-x' and save its metadata to 'paper.jsonl'.",
      "expected_output": "The agent should use 'echo ... | pyalex from-ids --jsonl-file paper.jsonl'.",
      "files": []
    }
  ]
}
```

- [ ] **Step 2: Commit test cases**

```bash
git add pyalex/agents/pyalex-cli-agent/evals/evals.json
git commit -m "test: add initial evals for pyalex-cli-agent skill"
```
