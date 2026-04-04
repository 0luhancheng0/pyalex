# Spec: PyAlex CLI Agent Skill

A modular, scenario-based skill designed to empower an AI agent to autonomously use the PyAlex CLI for scholarly research, data collection, and bibliometric analysis.

## Goals
- Enable the AI agent to search, filter, and retrieve data from OpenAlex using the `pyalex` CLI.
- Provide clear guidance on command patterns for discovery, bulk export, and data analysis.
- Maintain a lean context by using a modular "router" architecture.

## Triggering
The skill should trigger when the user asks for:
- Scholarly works, papers, or publications.
- Information about specific authors, institutions, funders, or topics.
- Bibliometric data (citations, open access status, publication years).
- Any mention of "OpenAlex", "PyAlex", "PyAlex CLI", or "OpenAlex IDs/DOIs".

## Architecture
The skill follows a modular **Scenario-Based Router** pattern:

1. **`SKILL.md` (Main Router)**
   - Identifies user intent.
   - Routes the agent to one of three specialized reference files using the `read_file` tool.
   - Provides a "Quick Reference" for common flags (`--limit`, `--jsonl-file`, `--all`).

2. **`references/searching.md` (Discovery & Filtering)**
   - Syntax for `works`, `authors`, `institutions`, etc.
   - Filter cheat sheet (e.g., `--year`, `--cited-by-count`, `--search`, `--type`, `--author-ids`).
   - Sorting and pagination logic.

3. **`references/data_export.md` (Retrieval & Export)**
   - `from-ids` command for bulk processing.
   - Saving results to JSONL files.
   - Piping IDs and the `show` command for tabular display.

4. **`references/analysis.md` (Grouping & Aggregation)**
   - `--group-by` parameter usage and common targets (e.g., `publication_year`, `oa_status`).
   - Combining grouping with filters for targeted analysis.

## Implementation Details

### Routing Logic
- **Discovery**: Task involves finding entities by criteria -> `searching.md`.
- **Collection**: Task involves downloading, bulk IDs, or export -> `data_export.md`.
- **Analysis**: Task involves grouping, distributions, or counts -> `analysis.md`.

### Safety & Constraints
- Always respect OpenAlex rate limits (automatically handled by the CLI, but agent should be aware of large `--all` queries).
- Prefer `--jsonl-file` for large datasets to avoid overflowing terminal buffers.
- Use `--dry-run` if the agent is unsure of a complex command's impact.

## Success Criteria
- The agent can correctly construct complex `pyalex works` commands with multiple filters.
- The agent can resolve a list of DOIs or IDs to metadata files.
- The agent can answer "What is the distribution of..." questions using `--group-by`.
