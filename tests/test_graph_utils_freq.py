import rustworkx as rx
import pytest
from experiments.graph_utils import build_indices, get_collaboration_counts

def test_get_collaboration_counts():
    graph = rx.PyDiGraph()
    
    # Authors
    a1 = graph.add_node({"type": "author", "id": "A1"})
    a2 = graph.add_node({"type": "author", "id": "A2"})
    a3 = graph.add_node({"type": "author", "id": "A3"})
    
    # Works post-cutoff (cutoff=2020)
    w1 = graph.add_node({"type": "work", "id": "W1", "year": 2021})
    w2 = graph.add_node({"type": "work", "id": "W2", "year": 2022})
    w3 = graph.add_node({"type": "work", "id": "W3", "year": 2021})
    
    # Work pre-cutoff
    w4 = graph.add_node({"type": "work", "id": "W4", "year": 2019})
    
    # Authorship edges
    # A1 and A2 share W1 and W2 (post-cutoff)
    graph.add_edge(a1, w1, {"type": "authorship"})
    graph.add_edge(a2, w1, {"type": "authorship"})
    graph.add_edge(a1, w2, {"type": "authorship"})
    graph.add_edge(a2, w2, {"type": "authorship"})
    
    # A1 and A3 share W3 (post-cutoff)
    graph.add_edge(a1, w3, {"type": "authorship"})
    graph.add_edge(a3, w3, {"type": "authorship"})
    
    # A2 and A3 share W4 (pre-cutoff)
    graph.add_edge(a2, w4, {"type": "authorship"})
    graph.add_edge(a3, w4, {"type": "authorship"})
    
    type_map, idx_to_id = build_indices(graph)
    eligible_authors = {"A1", "A2", "A3"}
    
    # This should fail if not implemented
    counts = get_collaboration_counts(graph, type_map, idx_to_id, 2020, eligible_authors)
    
    # Pair keys are sorted alphabetically
    assert counts[("A1", "A2")] == 2
    assert counts[("A1", "A3")] == 1
    assert ("A2", "A3") not in counts
    assert len(counts) == 2
