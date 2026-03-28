# Spec: Embedding Aggregation Enhancements

**Date:** 2026-03-28
**Status:** Draft
**Topic:** Implementing exponential temporal decay and token-limit guardrails for embedding aggregation.

## 1. Goal
Improve the robustness and accuracy of author-level embedding aggregation by replacing linear temporal decay with exponential decay and implementing smart truncation for concatenated abstracts.

## 2. Features

### 2.1 Exponential Temporal Decay
- **Current state**: Linear decay $1 / (\Delta t + 1)$.
- **Target state**: Exponential decay $e^{-\lambda \Delta t}$, where $\Delta t = \text{cutoff\_year} - \text{pub\_year}$.
- **Parameter**: $\lambda$ (decay rate), configurable via CLI. Default = $0.1$.
- **Normalization**: Weights are normalized to sum to $1.0$.

### 2.2 `concat_abstracts` Guardrail (Strategy C)
- **Goal**: Prevent token limit overflow while maintaining maximum relevance.
- **Strategy**: Prioritize recent abstracts (most relevant context) and truncate older ones if the limit is exceeded.
- **Limit**: Configurable via CLI. Default = $32768$.
- **Estimation**: Use a simple character-to-token heuristic ($1$ token $\approx 4$ characters) or word count if a full tokenizer is not accessible.
- **Warning**: Log a warning if truncation occurs.

## 3. Architecture

### 3.1 CLI Interface
The `evaluate` command in `collaboration_prediction.py` will be updated:
- `--decay-rate`: `float` (default: $0.1$).
- `--max-tokens`: `int` (default: $32768$).

### 3.2 Logic Flow
1.  `collaboration_prediction.py` parses CLI arguments.
2.  `aggregations.py` receives `decay_rate` and `max_tokens` via `compute_all_strategies`.
3.  `aggregate_recency_weighted` applies $e^{-\lambda \Delta t}$.
4.  `aggregate_concat_abstracts` sorts by year, concatenates until `max_tokens` is hit, and logs warnings.

## 4. Implementation Details

### 4.1 `aggregations.py`
- Update `aggregate_recency_weighted` signature and implementation.
- Update `aggregate_concat_abstracts` to accept `years` and `max_tokens`.
- Sort `texts` by `years` descending before concatenation.

### 4.2 `collaboration_prediction.py`
- Add `decay_rate` and `max_tokens` to `evaluate` command using `Annotated[..., typer.Option]`.

## 5. Verification Plan

### 5.1 Automated Tests
- Test exponential decay weights for known $\Delta t$ and $\lambda$.
- Test truncation logic: provide many abstracts and a small `max_tokens` limit, verify only the most recent are included.

### 5.2 Manual Verification
- Run `evaluate` with different `--decay-rate` values and observe changes in metrics (AUC, AP).
- Run `evaluate` with a very small `--max-tokens` (e.g., 100) to trigger truncation warnings.
