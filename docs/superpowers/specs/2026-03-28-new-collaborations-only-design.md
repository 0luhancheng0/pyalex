# Spec: New Collaborations Only (Temporal Split Enforcement)

**Date:** 2026-03-28
**Status:** Draft
**Topic:** Filtering repeat collaborations to ensure link prediction measures true "discovery."

## 1. Goal
Ensure that the collaboration prediction experiment measures the model's ability to predict *new* partnerships rather than simply recognizing existing ones. By default, the `sample` command will filter out any author pairs that have collaborated prior to the cutoff year.

## 2. Implementation Logic

### 2.1 Graph Analysis
1.  **Identify Pre-Cutoff Links**: Traverse the graph and identify all author pairs $(A, B)$ that shared a work published on or before the `cutoff_year`. Store these in a `pre_cutoff_positives` set.
2.  **Identify Post-Cutoff Links**: Identify all author pairs $(A, B)$ that shared a work published after the `cutoff_year`. Store these in a `post_cutoff_positives` set.
3.  **Filter**: Compute `new_positives = post_cutoff_positives - pre_cutoff_positives`.

### 2.2 Functional Changes

#### `graph_utils.py`
- Add `get_pre_cutoff_coauthor_pairs(graph, type_map, idx_to_id, cutoff_year, eligible_authors)`: Returns a set of author ID tuples who collaborated $\le$ `cutoff_year`.

#### `pipeline.py`
- Update `sample_pairs`:
    - Call `get_pre_cutoff_coauthor_pairs`.
    - Subtract these from the result of `get_post_cutoff_coauthor_pairs`.
    - Log statistics about filtered pairs.

#### `collaboration_prediction.py` (CLI)
- Update the `sample` command output to display:
    - Total post-cutoff collaborations found.
    - Number of repeat collaborations filtered.
    - Final number of new collaborations used for sampling.

## 3. Architecture Benefits
- **Discriminative Power**: Forces the model to use semantic similarity (embeddings) to predict future links that do not yet exist in the graph.
- **Scientific Rigor**: Adheres to the "cold-start" or "discovery" link prediction task, which is more challenging and useful for recommendation systems.

## 4. Verification Plan

### 4.1 Automated Tests
- Test filtering logic with a small mock graph containing:
    - Pair 1: Collaborated only pre-cutoff.
    - Pair 2: Collaborated only post-cutoff.
    - Pair 3: Collaborated both pre and post-cutoff.
- Verify only Pair 2 is returned as a "positive."

### 4.2 Manual Verification
- Run `sample` on the `cs_2017_2018` dataset.
- Confirm that the number of positives is lower than before and that the filtered count is non-zero.
