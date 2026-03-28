import numpy as np
import pytest
from experiments.aggregations import aggregate_recency_weighted

def test_aggregate_recency_weighted_exponential():
    # Setup: 3 embeddings of size 2
    embeddings = [
        np.array([1.0, 1.0], dtype=np.float32),
        np.array([2.0, 2.0], dtype=np.float32),
        np.array([3.0, 3.0], dtype=np.float32),
    ]
    years = [2020, 2021, 2022]
    cutoff_year = 2022
    
    # We expect exponential decay: e^(-lambda * delta_t)
    # delta_t = [2, 1, 0]
    # For lambda = 0.1 (default):
    # weights = [e^(-0.2), e^(-0.1), e^(0)]
    # weights = [0.8187, 0.9048, 1.0]
    # sum = 2.7235
    # normalized = [0.3006, 0.3322, 0.3672]
    
    # Let's test with a specific lambda if we add it as a parameter
    # For now, let's just ensure it's different from the linear one
    # Linear weights were: [1/(2+1), 1/(1+1), 1/(0+1)] = [1/3, 1/2, 1]
    # sum = 1.8333
    # normalized = [0.1818, 0.2727, 0.5455]
    
    result = aggregate_recency_weighted(embeddings, years, cutoff_year, lambda_val=0.1)
    
    # Verify shape
    assert result.shape == (2,)
    
    # Verify it's float32
    assert result.dtype == np.float32

    # Manually calculate expected for lambda=0.1
    delta_ts = np.array([2, 1, 0])
    expected_weights = np.exp(-0.1 * delta_ts)
    expected_weights /= expected_weights.sum()
    expected_result = (expected_weights[:, None] * np.stack(embeddings)).sum(axis=0)
    
    np.testing.assert_allclose(result, expected_result, rtol=1e-5)

def test_aggregate_recency_weighted_future_years():
    # Test that years > cutoff_year are treated as delta_t = 0
    embeddings = [np.array([1.0], dtype=np.float32), np.array([2.0], dtype=np.float32)]
    years = [2022, 2025]
    cutoff_year = 2022
    
    # delta_t = [0, 0] (since 2025 > 2022)
    # weights = [1, 1], normalized = [0.5, 0.5]
    # result = 1.5
    
    result = aggregate_recency_weighted(embeddings, years, cutoff_year)
    assert result[0] == 1.5
