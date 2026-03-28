import rustworkx as rx
import pytest
from experiments.pipeline import sample_pairs
from experiments.graph_utils import build_indices

def test_sample_pairs_subtraction():
    graph = rx.PyDiGraph()
    
    # Authors
    a1 = graph.add_node({"type": "author", "id": "A1"})
    a2 = graph.add_node({"type": "author", "id": "A2"})
    a3 = graph.add_node({"type": "author", "id": "A3"})
    a4 = graph.add_node({"type": "author", "id": "A4"})
    
    # Works pre-cutoff (cutoff=2020)
    w1 = graph.add_node({"type": "work", "id": "W1", "year": 2019})
    # A1 and A2 collaborated in 2019
    graph.add_edge(a1, w1, {"type": "authorship"})
    graph.add_edge(a2, w1, {"type": "authorship"})
    
    # Works post-cutoff (cutoff=2020)
    w2 = graph.add_node({"type": "work", "id": "W2", "year": 2021})
    w3 = graph.add_node({"type": "work", "id": "W3", "year": 2021})
    
    # A1 and A2 collaborated AGAIN in 2021 (repeat)
    graph.add_edge(a1, w2, {"type": "authorship"})
    graph.add_edge(a2, w2, {"type": "authorship"})
    
    # A1 and A3 collaborated for the FIRST time in 2021 (new)
    graph.add_edge(a1, w3, {"type": "authorship"})
    graph.add_edge(a3, w3, {"type": "authorship"})
    
    type_map, idx_to_id = build_indices(graph)
    eligible = {"A1", "A2", "A3", "A4"}
    
    # sample_pairs(graph, type_map, idx_to_id, eligible, cutoff_year, neg_ratio, neg_strategy, seed)
    positives, negatives, counts = sample_pairs(
        graph, type_map, idx_to_id, eligible,
        cutoff_year=2020,
        neg_ratio=1,
        neg_strategy="random",
        seed=42
    )
    
    # (A1, A2) is a repeat, so it should be filtered out.
    # (A1, A3) is new, so it should remain.
    
    # Positive pairs are sorted (id1, id2) where id1 < id2
    assert ("A1", "A3") in positives
    assert ("A1", "A2") not in positives
    assert len(positives) == 1
    assert counts["total_post_cutoff"] == 2
    assert counts["repeat"] == 1
    assert counts["new"] == 1
    
    # We requested neg_ratio=1, so we should have 1 negative pair.
    assert len(negatives) == 1
