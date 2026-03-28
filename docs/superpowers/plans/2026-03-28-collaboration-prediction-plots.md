# Collaboration Prediction Visualization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a comprehensive suite of visualization and diagnostic tools for collaboration prediction experiments, integrated into the existing CLI.

**Architecture:** Enhances `visualisation.py` with multi-strategy calibration and error stratification plots, and adds a `plot` command group to `collaboration_prediction.py` to expose these tools.

**Tech Stack:** Python, Matplotlib, Seaborn, Scikit-learn, Pandas, Typer.

---

### Task 1: Environment & Dependencies

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add seaborn and statsmodels to dependencies**
Modify `pyproject.toml` to include `seaborn` and `statsmodels`.

- [ ] **Step 2: Sync dependencies**
Run: `uv sync`

- [ ] **Step 3: Commit**
```bash
git add pyproject.toml
git commit -m "chore: add visualization dependencies (seaborn, statsmodels)"
```

### Task 2: Enhance `visualisation.py` for Calibration

**Files:**
- Modify: `experiments/visualisation.py`
- Test: `tests/test_visualisation.py` (Create)

- [ ] **Step 1: Write tests for multi-strategy calibration plotting**
```python
import numpy as np
from experiments.visualisation import plot_calibration

def test_plot_calibration_multi():
    y_true = np.array([0, 0, 1, 1])
    # Single strategy
    y_prob = {"model": np.array([0.1, 0.4, 0.35, 0.8])}
    fig = plot_calibration(y_true, y_prob)
    assert fig is not None
    
    # Multi strategy
    y_prob_multi = {
        "strat1": np.array([0.1, 0.4, 0.35, 0.8]),
        "strat2": np.array([0.2, 0.3, 0.6, 0.9])
    }
    fig = plot_calibration(y_true, y_prob_multi)
    assert fig is not None
```

- [ ] **Step 2: Update `plot_calibration` to support dict of probabilities**
Update the function signature and implementation to handle `dict[str, np.ndarray]`.

- [ ] **Step 3: Run tests**
Run: `pytest tests/test_visualisation.py`

- [ ] **Step 4: Commit**
```bash
git add experiments/visualisation.py tests/test_visualisation.py
git commit -m "feat: enhance calibration plot to support multiple strategies"
```

### Task 3: Implement Error Stratification Plots

**Files:**
- Modify: `experiments/visualisation.py`

- [ ] **Step 1: Add `plot_stratified_errors` implementation**
Ensure it supports categorical and binned numeric strata using Seaborn.

- [ ] **Step 2: Update tests**
Add a test case for `plot_stratified_errors` in `tests/test_visualisation.py`.

- [ ] **Step 3: Commit**
```bash
git add experiments/visualisation.py tests/test_visualisation.py
git commit -m "feat: implement stratified error visualization"
```

### Task 4: Integrate `plot` Command Group in CLI

**Files:**
- Modify: `experiments/collaboration_prediction.py`

- [ ] **Step 1: Add `plot` Typer app and subcommands**
Define `@plot_app.command("calibration")`, `@plot_app.command("stratified")`, and `@plot_app.command("diagnostics")`.

- [ ] **Step 2: Implement `calibration` command logic**
Load `predictions.json`, extract probabilities/labels, and call `plot_calibration`.

- [ ] **Step 3: Implement `stratified` command logic**
Load `predictions.json` and optionally `network.graphml`. Compute strata (e.g., author degree, work count) and plot.

- [ ] **Step 4: Implement `diagnostics` command logic**
Generate a summary report (text/markdown) and save Top-N errors.

- [ ] **Step 5: Commit**
```bash
git add experiments/collaboration_prediction.py
git commit -m "feat: add plot command group and subcommands to CLI"
```

### Task 5: End-to-End Validation

**Files:**
- Test: `experiments/collaboration_prediction.py` (Manual run)

- [ ] **Step 1: Run evaluation with predictions output**
`python experiments/collaboration_prediction.py evaluate data/cs_2017_2018/network.graphml --predictions-output preds.json`

- [ ] **Step 2: Generate calibration plot**
`python experiments/collaboration_prediction.py plot calibration preds.json -o calibration.png`

- [ ] **Step 3: Generate stratified plot**
`python experiments/collaboration_prediction.py plot stratified preds.json --graphml data/cs_2017_2018/network.graphml -o stratified.png`

- [ ] **Step 4: Verify outputs**
Ensure PNG files are generated and look correct.
