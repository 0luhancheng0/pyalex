# Spec: Advanced Evaluation Metrics

**Date:** 2026-03-28
**Status:** Draft
**Topic:** Implementing nDCG and relevance scores for collaboration prediction evaluation.

## 1. Goal
Improve the evaluation of link prediction models by incorporating ranking-aware metrics (nDCG) and using collaboration frequency as a multi-level relevance score.

## 2. Features

### 2.1 Relevance Score Computation (On-the-Fly)
- **Goal**: Measure the intensity of collaboration after the cutoff.
- **Implementation**:
    - During the `evaluate` command, if a GraphML file is available, compute the number of shared works between each positive pair published *after* the `cutoff_year`.
    - This count becomes the `relevance_score` for the pair.
    - Negative pairs are assigned a `relevance_score` of $0$.
- **Dependency**: Requires access to the GraphML file during the `evaluate` phase.

### 2.2 nDCG Implementation
- **Goal**: Evaluate the quality of the predicted rankings, giving higher weight to identifying frequent collaborators.
- **Metric**: Normalized Discounted Cumulative Gain (nDCG).
- **Processing**:
    - For each author (query), rank all candidate pairs (positive and negative) based on the model's similarity score.
    - Compute the nDCG score for this ranking using the ground-truth collaboration frequencies.
    - Report the Mean nDCG across all authors.

## 3. Architecture

### 3.1 `metrics.py`
- Update `evaluate_strategy` to:
    - Accept an optional `relevance_map: dict[tuple[str, str], int]`.
    - Compute `ndcg_score` per author if the `relevance_map` is provided.

### 3.2 `collaboration_prediction.py`
- Update the `evaluate` command:
    - Use `get_post_cutoff_coauthor_pairs` (or a similar internal helper) to count joint works per pair.
    - Pass the resulting `relevance_map` to `evaluate_strategy`.
    - Display the `nDCG` metric in the summary table.

## 4. Implementation Details

### 4.1 Computing Collaboration Frequency
```python
relevance_map = {}
for a1, a2 in positive_pairs:
    # count shared works published > cutoff_year
    count = count_shared_works(graph, a1, a2, cutoff_year)
    relevance_map[(a1, a2)] = count
```

### 4.2 Scoring with `ndcg_score`
```python
from sklearn.metrics import ndcg_score

# For each author query:
y_true = np.array([relevance_map.get(pair, 0) for pair in author_pairs])
y_score = np.array([model_similarities[pair] for pair in author_pairs])
score = ndcg_score([y_true], [y_score])
```

## 5. Verification Plan

### 5.1 Automated Tests
- Test `count_shared_works` logic with a mock graph.
- Test `evaluate_strategy` with a known `relevance_map` and verify the nDCG calculation.

### 5.2 Manual Verification
- Run `evaluate` on the `minimal_example` and `cs_2017_2018` datasets.
- Ensure the `nDCG` column is populated and changes reasonably with different aggregation strategies.
