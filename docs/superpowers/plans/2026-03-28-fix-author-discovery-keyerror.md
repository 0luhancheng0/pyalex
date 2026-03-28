# Fix Author Discovery KeyError Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the `KeyError` in `discover_authors.py` that occurs when a topic fails to return any authors.

**Architecture:** Initialize the `topic_authors` dictionary with empty sets for all topics in the `TOPICS` list. This ensures that the later intersection logic doesn't fail if a particular topic's author set remains empty due to API issues or lack of results.

**Tech Stack:** Python

---

### Task 1: Update discover_authors.py

**Files:**
- Modify: `experiments/datasets/trajectories/discover_authors.py`

- [ ] **Step 1: Initialize topic_authors with empty sets**

Modify the `discover()` function to initialize the dictionary.

```python
def discover():
    # Initialize with empty sets to avoid KeyError later if a topic returns no results
    topic_authors = {tid: set() for tid in TOPICS}
    
    # We'll use a temporary file for expand input
```

- [ ] **Step 2: Commit changes**

```bash
git add experiments/datasets/trajectories/discover_authors.py
git commit -m "fix: initialize topic_authors to avoid KeyError if topic results are empty"
```

### Task 2: Verification (Manual)

- [ ] **Step 1: Run the script**

Run the script directly to see if it handles empty results gracefully.

Run: `uv run experiments/datasets/trajectories/discover_authors.py`
Expected: The script should no longer crash with a KeyError even if it prints "No authors found in at least 2 topics."
