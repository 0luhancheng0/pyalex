import numpy as np
import rustworkx as rx
from typing import Dict, Tuple
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.neighbors import NearestNeighbors

def evaluate_link_prediction(
    graph: rx.PyGraph | rx.PyDiGraph, 
    embeddings: Dict[str, np.ndarray], 
    target_entity_type: str = "author",
    k: int = 10
) -> float:
    """
    Evaluation Option 2: Co-authorship / Collaboration Link Prediction
    
    Checks if an entity's nearest neighbors in the embedding space 
    include other entities they are actually connected to in the graph
    (e.g., co-authors, co-institutions).
    
    Returns Hit@K score.
    """
    # 1. Extract ground truth edges between target entities
    ground_truth_edges = set()
    is_directed = isinstance(graph, rx.PyDiGraph)
    
    # We define a "connection" between Author A and Author B if they share a Work.
    # In PyAlex graph, Author <-> Work <-> Author means co-authorship.
    
    entity_to_works = {}
    for node_idx in graph.node_indices():
        attrs = graph.get_node_data(node_idx) or {}
        
        # PyAlex stores the entity type in 'type'. 'source' typically means the anchor Work, 'target' means other Works,
        # but Authors get 'author', Institutions get 'institution', etc.
        node_type = attrs.get("type", "")
        
        # Target node determination
        if node_type != target_entity_type:
            continue
            
        entity_id = attrs.get("id", f"node_{node_idx}")
        if not entity_id or entity_id not in embeddings:
            continue
            
        works = set()
        neighbors = set(graph.predecessor_indices(node_idx)) | set(graph.successor_indices(node_idx)) if is_directed else set(graph.neighbors(node_idx))
        for n_idx in neighbors:
            n_attrs = graph.get_node_data(n_idx) or {}
            n_type = n_attrs.get("type", "")
            # We assume anything that is not 'author', 'institution', etc. is a work (or 'source' / 'target')
            if n_type not in ("author", "institution", "concept"):
                works.add(n_attrs.get("id", f"node_{n_idx}"))
        entity_to_works[entity_id] = works
        
    # Build co-occurrence map
    entity_ids = list(entity_to_works.keys())
    if len(entity_ids) < 2:
        return 0.0
        
    for i in range(len(entity_ids)):
        for j in range(i + 1, len(entity_ids)):
            e1 = entity_ids[i]
            e2 = entity_ids[j]
            # If they share at least one work, they are connected
            if not entity_to_works[e1].isdisjoint(entity_to_works[e2]):
                ground_truth_edges.add((e1, e2))
                ground_truth_edges.add((e2, e1))
                
    if not ground_truth_edges:
        print("Warning: No co-occurrence edges found between target entities.")
        return 0.0

    # 2. Fit KNN on Embeddings
    X = np.array([embeddings[eid] for e in entity_ids for eid in [e]]) # ensure order matches entity_ids
    
    if len(X) <= k:
        k = len(X) - 1
        
    if k == 0:
        return 0.0

    nbrs = NearestNeighbors(n_neighbors=k+1, algorithm='auto', metric='cosine').fit(X)
    distances, indices = nbrs.kneighbors(X)
    
    # 3. Calculate Hit@K
    hits = 0
    total_queries = 0
    
    for i, entity_id in enumerate(entity_ids):
        # We only care if this entity actually has ground truth connections
        actual_neighbors = {v for u, v in ground_truth_edges if u == entity_id}
        if not actual_neighbors:
            continue
            
        total_queries += 1
        
        # indices[i][0] is usually the node itself (distance 0). We look at [1:]
        predicted_neighbor_indices = indices[i][1:]
        predicted_neighbor_ids = [entity_ids[idx] for idx in predicted_neighbor_indices]
        
        # Did we find at least one actual neighbor in the top K?
        if any(pred_id in actual_neighbors for pred_id in predicted_neighbor_ids):
            hits += 1
            
    if total_queries == 0:
        return 0.0
        
    return hits / total_queries


def evaluate_semantic_consistency(
    graph: rx.PyGraph | rx.PyDiGraph, 
    embeddings: Dict[str, np.ndarray], 
    target_entity_type: str = "author"
) -> float:
    """
    Evaluation Option 3: Semantic Consistency (Work-to-Author Alignment)
    
    Measures the margin between:
    - Average Cosine Similarity of Author to their OWN Works
    - Average Cosine Similarity of Author to RANDOM Works
    
    A higher margin (closer to 1.0) means the embedding strongly represents
    the entity's specific domain content.
    """
    is_directed = isinstance(graph, rx.PyDiGraph)
    
    all_work_embeddings = []
    all_work_ids = []
    
    for node_idx in graph.node_indices():
        attrs = graph.get_node_data(node_idx) or {}
        node_type = attrs.get("type", "")
        is_work = node_type not in ("author", "institution", "concept")
        if is_work and "embedding" in attrs and isinstance(attrs["embedding"], np.ndarray):
            all_work_embeddings.append(attrs["embedding"])
            all_work_ids.append(attrs.get("id", f"node_{node_idx}"))
            
    if not all_work_embeddings:
        print("Warning: No Work embeddings found in graph.")
        return 0.0
        
    all_work_embeddings_matrix = np.array(all_work_embeddings)
    
    margins = []
    
    for node_idx in graph.node_indices():
        attrs = graph.get_node_data(node_idx) or {}
        node_type = attrs.get("type", "")
        
        if node_type != target_entity_type:
            continue
            
        entity_id = attrs.get("id", f"node_{node_idx}")
        if not entity_id or entity_id not in embeddings:
            continue
            
        entity_emb = embeddings[entity_id].reshape(1, -1)
        
        # Get own works
        own_work_embs = []
        neighbors = set(graph.predecessor_indices(node_idx)) | set(graph.successor_indices(node_idx)) if is_directed else set(graph.neighbors(node_idx))
        for n_idx in neighbors:
            n_attrs = graph.get_node_data(n_idx) or {}
            n_type = n_attrs.get("type", "")
            n_is_work = n_type not in ("author", "institution", "concept")
            if n_is_work and "embedding" in n_attrs and isinstance(n_attrs["embedding"], np.ndarray):
                own_work_embs.append(n_attrs["embedding"])
                
        if not own_work_embs:
            continue
            
        # Similarity to own works
        sim_own = cosine_similarity(entity_emb, np.array(own_work_embs)).mean()
        
        # Similarity to random works
        # Select random works, ensure we don't pick own works if possible
        # For simplicity, we just pick from all works. If graph is huge, overlap is negligible.
        num_random = min(10, len(all_work_embeddings_matrix))
        random_indices = np.random.choice(len(all_work_embeddings_matrix), num_random, replace=False)
        random_work_embs = all_work_embeddings_matrix[random_indices]
        
        sim_random = cosine_similarity(entity_emb, random_work_embs).mean()
        
        margins.append(sim_own - sim_random)
        
    if not margins:
        return 0.0
        
    return float(np.mean(margins))
