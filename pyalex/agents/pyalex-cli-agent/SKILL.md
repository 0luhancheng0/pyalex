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
