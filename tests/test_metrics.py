import numpy as np
import pytest
from experiments.metrics import evaluate_strategy

def test_evaluate_strategy_with_ndcg():
    # Setup
    embeddings = {
        "A": np.array([1.0, 0.0]),
        "B": np.array([0.9, 0.1]),
        "C": np.array([0.1, 0.9]),
        "D": np.array([0.0, 1.0]),
    }
    # Positive pairs: (A, B) and (C, D)
    positive_pairs = {("A", "B"), ("C", "D")}
    # Negative pairs: (A, C) and (B, D)
    negative_pairs = [("A", "C"), ("B", "D")]
    
    # Relevance map (collaboration counts)
    relevance_map = {
        ("A", "B"): 10,
        ("C", "D"): 5,
    }
    
    # Evaluate
    # This will fail until evaluate_strategy is updated to accept relevance_map
    results = evaluate_strategy(
        embeddings,
        positive_pairs,
        negative_pairs,
        relevance_map=relevance_map
    )
    
    # Check if nDCG is present
    assert "ndcg" in results
    assert results["ndcg"] > 0
    assert results["ndcg"] <= 1.0
    
    # In this specific case, A is connected to B (score ~0.99) and C (score ~0.1)
    # So A's ranking is [B, C], which is perfect.
    # C is connected to D (score ~0.99) and A (score ~0.1)
    # So C's ranking is [D, A], which is perfect.
    # Thus nDCG should be close to 1.0
    assert results["ndcg"] == pytest.approx(1.0, rel=0.1)

def test_evaluate_strategy_no_relevance_map():
    # Setup
    embeddings = {
        "A": np.array([1.0, 0.0]),
        "B": np.array([0.9, 0.1]),
        "C": np.array([0.1, 0.9]),
        "D": np.array([0.0, 1.0]),
    }
    # Positive pairs
    positive_pairs = {("A", "B"), ("C", "D")}
    # Negative pairs
    negative_pairs = [("A", "C"), ("B", "D")]
    
    # Evaluate
    results = evaluate_strategy(
        embeddings,
        positive_pairs,
        negative_pairs
    )
    
    # nDCG should still be calculated but with binary relevance
    assert "ndcg" in results
    assert results["ndcg"] == pytest.approx(1.0, rel=0.1)
