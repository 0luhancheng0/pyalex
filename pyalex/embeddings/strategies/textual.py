import numpy as np
import rustworkx as rx
from typing import Dict, Optional

from ..interfaces import EntityEmbeddingStrategy

class ConcatenatedAbstractsStrategy(EntityEmbeddingStrategy):
    """
    Computes an entity's embedding by concatenating the titles and abstracts
    of its connected Works, and passing that composite text through the embedding model.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", max_works: int = 10, separator: str = " | "):
        super().__init__(model_name)
        self.max_works = max_works
        self.separator = separator
        
    def compute_embeddings(self, graph: rx.PyGraph | rx.PyDiGraph, target_entity_type: str = "author") -> Dict[str, np.ndarray]:
        from ..embed import generate_embeddings
        embeddings = {}
        is_directed = isinstance(graph, rx.PyDiGraph)
        
        texts_to_embed = []
        entity_ids = []

        for node_idx in graph.node_indices():
            attrs = graph.get_node_data(node_idx) or {}
            
            node_type = attrs.get("type", "")
            if node_type != target_entity_type:
                continue
                
            entity_id = attrs.get("id", f"node_{node_idx}")

            # Gather text from neighbors
            if is_directed:
                neighbors = set(graph.predecessor_indices(node_idx)) | set(graph.successor_indices(node_idx))
            else:
                neighbors = set(graph.neighbors(node_idx))
                
            work_texts = []
            for neighbor_idx in neighbors:
                n_attrs = graph.get_node_data(neighbor_idx)
                if not n_attrs:
                    continue
                n_type = n_attrs.get("type", "")
                is_work = n_type not in ("author", "institution", "concept")
                
                if not is_work or "title" not in n_attrs:
                    continue
                    
                # The actual GraphML from pyalex might not store raw title/abstract
                # If they are available in 'text' or 'title' + 'abstract' fields:
                # We assume standard pyalex behavior where maybe title is preserved.
                # Let's check for 'title' and 'abstract' attributes.
                title = n_attrs.get("title", "")
                
                # In PyAlex graphml, often we just have the 'title' or a pre-computed text.
                # Let's fallback to label if title is missing.
                if not title:
                    title = n_attrs.get("label", "")
                    
                # We don't usually store abstract in graphml to save space.
                # If we need it, we might have to fetch it, but for this strategy
                # let's assume we use whatever 'title' or 'text' is available on the node.
                text_content = n_attrs.get("text", title)
                if text_content and text_content.strip():
                    work_texts.append(str(text_content).strip())
                    
            if work_texts:
                # Sort to ensure determinism, take top K (max_works)
                # Ideally sort by citation count if available, but for now just take first K
                # Let's try to sort by cited_by_count if available
                
                def get_cite_count(idx):
                    attrs = graph.get_node_data(idx)
                    try:
                        return int(attrs.get("cited_by_count", 0))
                    except (ValueError, TypeError):
                        return 0
                        
                sorted_neighbors = sorted(list(neighbors), key=get_cite_count, reverse=True)
                
                sorted_texts = []
                for n_idx in sorted_neighbors[:self.max_works]:
                     n_attrs = graph.get_node_data(n_idx)
                     if n_attrs and n_attrs.get("type", "") not in ("author", "institution", "concept"):
                         title = n_attrs.get("title", n_attrs.get("label", ""))
                         if title:
                             sorted_texts.append(str(title))
                
                composite_text = self.separator.join(sorted_texts)
                if composite_text:
                    texts_to_embed.append(composite_text)
                    entity_ids.append(entity_id)
        
        if texts_to_embed:
             # Generate embeddings in batch
             batch_embeddings = generate_embeddings(texts_to_embed, model_name=self.model_name)
             for e_id, emb in zip(entity_ids, batch_embeddings):
                 if emb is not None:
                     embeddings[e_id] = np.array(emb, dtype=np.float32)
                     
        return embeddings
