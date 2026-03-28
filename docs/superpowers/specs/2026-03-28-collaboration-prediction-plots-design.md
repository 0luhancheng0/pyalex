# Spec: Collaboration Prediction Visualization Enhancements

**Date:** 2026-03-28
**Status:** Draft
**Topic:** Implementing visualization and diagnostic tools for collaboration prediction experiments.

## 1. Goal
Provide a comprehensive suite of visualization tools to analyze model performance, calibrate confidence, and identify systematic error patterns in the collaboration prediction experiments.

## 2. Architecture

### 2.1 CLI Interface
The `pyalex experiments collaboration-prediction` command will be expanded with a `plot` command group.

```bash
python collaboration_prediction.py plot <subcommand> [options]
```

#### Subcommands:
1.  **`calibration`**: Generates reliability diagrams to assess how well predicted similarities align with actual collaboration probabilities.
2.  **`stratified`**: Analyzes error rates (FP/FN) across different author/pair attributes.
3.  **`diagnostics`**: Generates a summary dashboard or directory of plots and statistics for a model.

### 2.2 Data Flow
- **Input**:
    - `predictions.json`: Produced by `evaluate --predictions-output`. Contains pairs, labels, and scores.
    - `network.graphml`: (Optional) Provides metadata for stratification (e.g., node attributes, network structure).
- **Processing**:
    - Data is loaded into Pandas DataFrames for efficient stratification and grouping.
    - `visualisation.py` provides the core plotting functions using Matplotlib/Seaborn.
- **Output**:
    - High-resolution plots (PNG/PDF).
    - Summary statistics (JSON/Markdown).

## 3. Features

### 3.1 Calibration Plots
- **Tool**: `sklearn.calibration.calibration_curve`.
- **Functionality**:
    - Support for multiple strategies in one plot (comparison mode).
    - Configurable binning (uniform vs. quantile).
    - Histogram of predicted probabilities (optional subplot).

### 3.2 Error Stratification
Stratify False Positives and False Negatives by:
- **Productivity**: Works per author (pre-cutoff).
- **Recency**: Years since last publication relative to cutoff.
- **Topic Similarity**: (If available) Lexical or concept overlap.
- **Network Features**: Common neighbors, shortest path distance in pre-cutoff graph.

### 3.3 Model Diagnostics
- Save feature vectors for misclassified pairs.
- Generate "Top N" lists of most egregious errors (high-confidence FPs, low-confidence FNs) with author names and metadata.
- Automated report generation.

## 4. Implementation Plan

### Phase 1: Core Visualization (`visualisation.py`)
- Refine existing `plot_calibration`.
- Implement `plot_stratified_errors` (multi-bar or heatmap).
- Implement `plot_feature_distribution_by_error` (violin or box plots).

### Phase 2: CLI Integration (`collaboration_prediction.py`)
- Add `plot` command group.
- Implement `calibration` subcommand (JSON input).
- Implement `stratified` subcommand (JSON + GraphML input).

### Phase 3: Diagnostics & Reporting
- Implement `diagnostics` subcommand.
- Add summary statistics export.

## 5. Verification Plan

### Automated Tests
- Test data loading from `predictions.json`.
- Verify plot generation does not raise exceptions.
- Test stratification logic with mock dataframes.

### Manual Verification
- Generate plots for the `minimal_example` dataset.
- Inspect output figures for correctness and aesthetic quality.
