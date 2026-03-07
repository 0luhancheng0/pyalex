import numpy as np
import rustworkx as rx
from typing import Dict

from interfaces import EntityEmbeddingStrategy

class AverageNeighborStrategy(EntityEmbeddingStrategy):
    """
    Computes an entity's embedding by averaging the embeddings of all its 
    directly connected neighboring nodes (usually Works) that possess an embedding.
    """

    def compute_embeddings(self, graph: rx.PyGraph | rx.PyDiGraph, target_entity_type: str = "author") -> Dict[str, np.ndarray]:
        embeddings = {}
        
        # In directed graphs from PyAlex, edges usually go Work -> Author.
        # To be safe and treat it generally, we can check predecessors and successors,
        # or if it's undirected, just neighbors.
        is_directed = isinstance(graph, rx.PyDiGraph)

        for node_idx in graph.node_indices():
            attrs = graph.get_node_data(node_idx) or {}
            
            node_type = attrs.get("type", "")
            if node_type != target_entity_type:
                continue
                
            entity_id = attrs.get("id", f"node_{node_idx}")

            neighbor_embeddings = []
            
            # Find all neighbors
            if is_directed:
                neighbors = set(graph.predecessor_indices(node_idx)) | set(graph.successor_indices(node_idx))
            else:
                neighbors = set(graph.neighbors(node_idx))
                
            for neighbor_idx in neighbors:
                n_attrs = graph.get_node_data(neighbor_idx)
                if n_attrs and "embedding" in n_attrs and isinstance(n_attrs["embedding"], np.ndarray):
                    neighbor_embeddings.append(n_attrs["embedding"])
            
            if neighbor_embeddings:
                # Average them
                avg_embedding = np.mean(neighbor_embeddings, axis=0)
                embeddings[entity_id] = avg_embedding
                
        return embeddings
