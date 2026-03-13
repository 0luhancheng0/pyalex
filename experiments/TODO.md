# Experiments TODO List

## Visualization and Analysis Enhancements

### 1. Calibration Plots
- [ ] Implement calibration plot functionality in `visualisation.py`
- [ ] Add calibration plotting to evaluation pipeline
- [ ] Generate calibration plots for each embedding strategy
- [ ] Analyze model confidence reliability

### 2. Error Stratification Analysis
- [ ] Add error stratification capabilities to evaluation
- [ ] Stratify false positives/negatives by:
    - Author productivity (works per author)
    - Publication recency (years relative to cutoff)
    - Topical distance between authors
    - Network features (common neighbors, centrality)
    - Citation impact (h-index, total citations)
- [ ] Implement visualization functions for stratified errors
- [ ] Generate stratified error plots for each dataset
- [ ] Identify systematic failure patterns

### 3. Model Diagnostics Extension
- [ ] Save prediction scores and probabilities during evaluation
- [ ] Store feature vectors for misclassified pairs
- [ ] Create error analysis dashboard
- [ ] Generate summary statistics of error types

### 4. Reporting and Documentation
- [ ] Create template for error analysis reports
- [ ] Document stratification methodology
- [ ] Add interpretation guidelines for calibration plots
- [ ] Create examples of common error patterns and solutions