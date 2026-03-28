import rustworkx as rx
import pytest
from experiments.graph_utils import build_indices, get_pre_cutoff_coauthor_pairs

def test_get_pre_cutoff_coauthor_pairs():
    graph = rx.PyDiGraph()
    
    # Authors
    a1 = graph.add_node({"type": "author", "id": "A1"})
    a2 = graph.add_node({"type": "author", "id": "A2"})
    a3 = graph.add_node({"type": "author", "id": "A3"})
    a4 = graph.add_node({"type": "author", "id": "A4"})
    
    # Works pre-cutoff (cutoff=2020)
    w1 = graph.add_node({"type": "work", "id": "W1", "year": 2019})
    w2 = graph.add_node({"type": "work", "id": "W2", "year": 2020})
    
    # Works post-cutoff
    w3 = graph.add_node({"type": "work", "id": "W3", "year": 2021})
    
    # Authorship edges
    # A1 and A2 collaborated in 2019 (pre-cutoff)
    graph.add_edge(a1, w1, {"type": "authorship"})
    graph.add_edge(a2, w1, {"type": "authorship"})
    
    # A2 and A3 collaborated in 2020 (at cutoff)
    graph.add_edge(a2, w2, {"type": "authorship"})
    graph.add_edge(a3, w2, {"type": "authorship"})
    
    # A1 and A4 collaborated in 2021 (post-cutoff)
    graph.add_edge(a1, w3, {"type": "authorship"})
    graph.add_edge(a4, w3, {"type": "authorship"})
    
    type_map, idx_to_id = build_indices(graph)
    eligible_authors = {"A1", "A2", "A3", "A4"}
    
    # cutoff_year=2020 means we look for works with year <= 2020
    pairs = get_pre_cutoff_coauthor_pairs(graph, type_map, idx_to_id, 2020, eligible_authors)
    
    assert ("A1", "A2") in pairs
    assert ("A2", "A3") in pairs
    assert ("A1", "A4") not in pairs
    assert len(pairs) == 2

    # Check that it handles a pair collaborating multiple times (should only be in the set once)
    w4 = graph.add_node({"type": "work", "id": "W4", "year": 2018})
    graph.add_edge(a1, w4, {"type": "authorship"})
    graph.add_edge(a2, w4, {"type": "authorship"})
    
    pairs_updated = get_pre_cutoff_coauthor_pairs(graph, type_map, idx_to_id, 2020, eligible_authors)
    assert len(pairs_updated) == 2
    assert ("A1", "A2") in pairs_updated
