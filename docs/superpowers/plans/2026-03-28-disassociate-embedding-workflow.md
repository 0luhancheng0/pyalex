# Disassociate Embedding Workflow from Experiments

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove experiment-specific arguments and logic from the generalist `pyalex embedding` subcommand.

**Architecture:** Simplify `pyalex/embeddings/embed.py` by removing specialized author aggregation strategies and cutoff year filtering. Update the CLI to remove corresponding options. Ensure experiments that rely on these features use a local version of the embedding script.

**Tech Stack:** Python, Typer, Pandas, Numpy

---

### Task 1: Preserve Experiment-Specific Embedding Logic

**Files:**
- Create: `experiments/datasets/cs_2017_2018/embed.py`
- Modify: `experiments/datasets/cs_2017_2018/Makefile`

- [ ] **Step 1: Copy current embedding script to the experiment directory**
Copy `pyalex/embeddings/embed.py` to `experiments/datasets/cs_2017_2018/embed.py` to ensure the experiment can still run with its specific requirements.

- [ ] **Step 2: Update Makefile to use local embedding script**
Modify `experiments/datasets/cs_2017_2018/Makefile` to call the local `embed.py` instead of `pyalex embedding generate`.

```makefile
embeddings.parquet: network.graphml embed.py
	uv run python embed.py generate $< $@ \
	    --author-cutoff-year $(CUTOFF_YEAR) \
	    --author-aggregation-strategy mean
```

- [ ] **Step 3: Verify experiment still works**
Run the experiment's embedding step to ensure it still functions correctly with the local script.
Run: `cd experiments/datasets/cs_2017_2018 && make embeddings.parquet`

---

### Task 2: Simplify PyAlex Embedding Subcommand

**Files:**
- Modify: `pyalex/embeddings/embed.py`

- [ ] **Step 1: Remove experiment-specific arguments from `generate` command**
Remove `author_cutoff_year` and `author_aggregation_strategy` from the `generate` function signature and its `typer.Option` definitions.

- [ ] **Step 2: Simplify `_embed_authors` function**
Remove `cutoff_year` and `aggregation_strategy` parameters. Update the logic to only use the simple mean aggregation and remove all year-based filtering.

- [ ] **Step 3: Remove specialized aggregation functions and enum**
Delete `AuthorAggregationStrategy` enum and functions: `_aggregate_recency_weighted`, `_aggregate_citation_weighted`, `_aggregate_max_pool`, `_aggregate_concat_abstracts`.

- [ ] **Step 4: Verify simplified CLI**
Run `pyalex embedding generate --help` and verify the options are gone.
Run: `uv run pyalex embedding generate --help`

---

### Task 3: Update Documentation

**Files:**
- Modify: `docs/embeddings.md`

- [ ] **Step 1: Remove experiment-specific options from documentation**
Remove references to `--author-cutoff-year` and `--author-aggregation-strategy` from the CLI examples in `docs/embeddings.md`.

---

### Task 4: Final Validation

- [ ] **Step 1: Run general embedding generation**
Verify that `pyalex embedding generate` still works for a general network graph.
Run: `uv run pyalex embedding generate tests/data/test_network.graphml test_output.parquet` (ensure a test graph exists or use an existing one).

- [ ] **Step 2: Commit changes**
Commit the cleaned up `pyalex` code and the updated experiment files.
