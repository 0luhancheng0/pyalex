import json
import numpy as np
import rustworkx as rx


def load_graphml_to_rx(file_path: str) -> rx.PyGraph:
    """
    Loads a PyAlex GraphML file into a rustworkx PyGraph.
    It parses the stringified 'embedding' attribute into a numpy array.
    """
    # rustworkx currently returns a PyDiGraph from read_graphml if the file indicates directed.
    # PyAlex network.graphml is generally directed. We'll use read_graphml and let it decide,
    # but we usually treat it as undirected for topological embedding methods.
    graph = rx.read_graphml(file_path)
    
    # It might return a list of graphs, but we usually have one.
    if isinstance(graph, list):
        graph = graph[0]

    # Process node attributes
    for node_idx in graph.node_indices():
        attrs = graph.get_node_data(node_idx)
        if attrs and "embedding" in attrs and isinstance(attrs["embedding"], str):
            try:
                # Convert string representation of list to numpy array
                embedding_list = json.loads(attrs["embedding"])
                attrs["embedding"] = np.array(embedding_list, dtype=np.float32)
                graph[node_idx] = attrs
            except (json.JSONDecodeError, ValueError) as e:
                print(f"Warning: Failed to parse embedding for node {node_idx}: {e}")
                
    return graph

def write_rx_to_graphml(graph: rx.PyGraph | rx.PyDiGraph, file_path: str):
    """
    Writes a rustworkx graph back to a GraphML file.
    Converts numpy array embeddings back to JSON strings.
    """
    # Create a copy so we don't modify the in-memory graph
    if isinstance(graph, rx.PyGraph):
        out_graph = graph.copy()
    else:
        out_graph = graph.copy()
        
    for node_idx in out_graph.node_indices():
        attrs = out_graph.get_node_data(node_idx)
        if attrs and "embedding" in attrs and isinstance(attrs["embedding"], np.ndarray):
            # Convert numpy array to list, then to JSON string
            attrs["embedding"] = json.dumps(attrs["embedding"].tolist())
            out_graph[node_idx] = attrs
            
    # Prepare nodes for writing: rustworkx infers keys from dicts, but they must be simple types
    for node_idx in out_graph.node_indices():
        attrs = out_graph.get_node_data(node_idx)
        if isinstance(attrs, dict):
            clean_node = {}
            for k, v in attrs.items():
                if v is not None:
                    clean_node[k] = str(v) if not isinstance(v, (int, float, str, bool)) else v
            out_graph[node_idx] = clean_node

    # Prepare edges for writing
    for edge_idx in out_graph.edge_indices():
        attrs = out_graph.get_edge_data_by_index(edge_idx)
        if isinstance(attrs, dict):
            clean_edge = {}
            for k, v in attrs.items():
                if v is not None:
                    clean_edge[k] = str(v) if not isinstance(v, (int, float, str, bool)) else v
            out_graph.update_edge_by_index(edge_idx, clean_edge)

    rx.write_graphml(out_graph, file_path)
