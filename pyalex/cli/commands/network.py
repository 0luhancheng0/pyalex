"""
Citation network builder command for PyAlex CLI.

This command builds a citation network from OpenAlex works using rustworkx and visualizes it with Plotly.
"""

import itertools
import json
from pathlib import Path
from typing import Annotated, List, Dict, Set, Any, Tuple, Optional

import typer

try:
    import rustworkx as rx
    from neo4j_viz import VisualizationGraph, Node, Relationship
except ImportError:
    rx = None
    VisualizationGraph = None
    Node = None
    Relationship = None

from ..utils import _handle_cli_exception
from .help_panels import VISUALIZATION_PANEL



def _load_works(input_files: List[Path]) -> Tuple[List[Dict], Dict[str, str], Set[str]]:
    """
    Load works from a list of JSONL files.
    
    Returns:
        Tuple containing:
        - List of work dictionaries
        - Map of work ID to source filename (stem)
        - Set of unique source filenames found
    """
    works_data = []
    work_source_map = {}
    source_files = set()

    for file_path in input_files:
        # Use stem (filename without extension) as the source label
        source_name = file_path.stem
        source_files.add(source_name)
        typer.echo(f"Reading works from {file_path} (labeled as '{source_name}')...")
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    work = json.loads(line)
                    works_data.append(work)
                    wid = work.get("id")
                    if wid and wid not in work_source_map:
                        work_source_map[wid] = source_name
                except json.JSONDecodeError:
                    continue
    
    typer.echo(f"Loaded {len(works_data)} works from {len(source_files)} files.")
    return works_data, work_source_map, source_files



def _flatten_dict_for_graph(d: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten a dict so all values are GraphML-safe scalars.

    Nested dicts and lists are serialised to JSON strings.
    None values are dropped.
    """
    flat: Dict[str, Any] = {}
    for k, v in d.items():
        if v is None:
            continue
        if isinstance(v, (dict, list)):
            flat[k] = json.dumps(v)
        else:
            flat[k] = v
    return flat


def _build_graph(
    works_data: List[Dict], 
    work_source_map: Dict[str, str], 
    edge_types: List[str], 
    include_external: bool
) -> Tuple[Any, Dict[str, int], int]:
    """
    Builds the PyDiGraph from works data.
    
    Returns:
        Tuple containing:
        - The constructed graph (rx.PyDiGraph)
        - Mapping of OpenAlex ID to node index
        - Count of external nodes added
    """
    graph = rx.PyDiGraph()
    id_to_idx = {}

    # Pass 1: Add nodes for all works in the file (Sources)
    for work in works_data:
        work_id = work.get("id")
        if work_id:
            # Clean ID if it's a URL
            work_id = work_id.replace("https://openalex.org/", "")
            if work_id not in id_to_idx:
                source_name = work_source_map.get(work.get("id"), "Unknown")

                # Extract citation_normalized_percentile
                percentile = 0.0
                if "citation_normalized_percentile" in work and work["citation_normalized_percentile"]:
                     percentile = float(work["citation_normalized_percentile"].get("value", 0.0))

                # Copy all attributes from the input JSONL
                node_data = _flatten_dict_for_graph(work)
                # Override / add graph-specific fields
                node_data["id"] = work_id
                node_data["type"] = "source"
                node_data["source_file"] = source_name
                node_data["year"] = int(work.get("publication_year") or 0)
                node_data["percentile"] = percentile

                idx = graph.add_node(node_data)
                id_to_idx[work_id] = idx

    external_node_count = 0

    # Pass 2: Add edges
    for et in edge_types:
        if et in ["citation", "related"]:
            edge_field = "referenced_works" if et == "citation" else "related_works"
            typer.echo(f"Adding '{et}' edges from field '{edge_field}'...")
    
            for work in works_data:
                source_id = work.get("id")
                if not source_id:
                    continue
    
                source_id = source_id.replace("https://openalex.org/", "")
                if source_id not in id_to_idx:
                    continue
                    
                source_idx = id_to_idx[source_id]
    
                targets = work.get(edge_field, [])
                for target_ref in targets:
                    target_id = target_ref.replace("https://openalex.org/", "")
                    
                    if target_id in id_to_idx:
                        # Internal edge
                        target_idx = id_to_idx[target_id]
                        if source_idx != target_idx:
                            graph.add_edge(source_idx, target_idx, {"type": et})
                    elif include_external:
                        # Add external node
                        if target_id not in id_to_idx:
                            idx = graph.add_node(
                                {
                                    "title": "External Work",
                                    "id": target_id,
                                    "type": "external",
                                    "source_file": "External",
                                    "year": 0,
                                    "percentile": 0.0,
                                }
                            )
                            id_to_idx[target_id] = idx
                            external_node_count += 1
    
                        target_idx = id_to_idx[target_id]
                        graph.add_edge(source_idx, target_idx, {"type": et})
        
        elif et == "authorship":
            typer.echo("Adding 'authorship' edges (Work -> Author)...")
            for work in works_data:
                source_id = work.get("id")
                if not source_id:
                    continue
                source_id = source_id.replace("https://openalex.org/", "")
                if source_id not in id_to_idx:
                    continue
                source_idx = id_to_idx[source_id]

                for authorship in work.get("authorships", []):
                    author = authorship.get("author", {})
                    if not author:
                        continue
                    author_id = author.get("id")
                    if not author_id:
                        continue
                    author_id = author_id.replace("https://openalex.org/", "")

                    if author_id not in id_to_idx:
                        node_data = _flatten_dict_for_graph(author)
                        node_data["title"] = author.get("display_name", "Unknown Author")
                        node_data["id"] = author_id
                        node_data["type"] = "author"
                        node_data["source_file"] = "Author"
                        node_data["year"] = 0
                        node_data["percentile"] = 0.0

                        idx = graph.add_node(node_data)
                        id_to_idx[author_id] = idx

                    author_idx = id_to_idx[author_id]
                    graph.add_edge(source_idx, author_idx, {"type": et})

        elif et == "affiliation":
            typer.echo("Adding 'affiliation' edges (Author -> Institution)...")
            for work in works_data:
                for authorship in work.get("authorships", []):
                    author = authorship.get("author", {})
                    if not author:
                        continue
                    author_id = author.get("id")
                    if not author_id:
                        continue
                    author_id = author_id.replace("https://openalex.org/", "")

                    # Authors should have been added by 'authorship' edge step, but if only 'affiliation' is used:
                    if author_id not in id_to_idx:
                        node_data = _flatten_dict_for_graph(author)
                        node_data["title"] = author.get("display_name", "Unknown Author")
                        node_data["id"] = author_id
                        node_data["type"] = "author"
                        node_data["source_file"] = "Author"
                        node_data["year"] = 0
                        node_data["percentile"] = 0

                        idx = graph.add_node(node_data)
                        id_to_idx[author_id] = idx
                    
                    author_idx = id_to_idx[author_id]

                    for inst in authorship.get("institutions", []):
                        inst_id = inst.get("id")
                        if not inst_id:
                            continue
                        inst_id = inst_id.replace("https://openalex.org/", "")

                        if inst_id not in id_to_idx:
                            node_data = _flatten_dict_for_graph(inst)
                            node_data["title"] = inst.get("display_name", "Unknown Institution")
                            node_data["id"] = inst_id
                            node_data["type"] = "institution"
                            node_data["source_file"] = "Institution"
                            node_data["year"] = 0
                            node_data["percentile"] = 0.0

                            idx = graph.add_node(node_data)
                            id_to_idx[inst_id] = idx

                        inst_idx = id_to_idx[inst_id]
                        graph.add_edge(author_idx, inst_idx, {"type": et})
        elif et == "collaboration":
            typer.echo("Adding 'collaboration' edges (Author <-> Author via shared works)...")
            for work in works_data:
                author_ids_in_work: list[str] = []
                for authorship in work.get("authorships", []):
                    author = authorship.get("author", {})
                    if not author:
                        continue
                    author_id = author.get("id")
                    if not author_id:
                        continue
                    author_id = author_id.replace("https://openalex.org/", "")

                    # Create author node if not yet in the graph
                    if author_id not in id_to_idx:
                        node_data = _flatten_dict_for_graph(author)
                        node_data["title"] = author.get("display_name", "Unknown Author")
                        node_data["id"] = author_id
                        node_data["type"] = "author"
                        node_data["source_file"] = "Author"
                        node_data["year"] = 0
                        node_data["percentile"] = 0.0
                        idx = graph.add_node(node_data)
                        id_to_idx[author_id] = idx

                    author_ids_in_work.append(author_id)

                # Add one undirected-style edge per unique co-author pair.
                # Sort IDs so the edge direction is deterministic and we don't
                # add the same pair twice for the same work.
                for a_id, b_id in itertools.combinations(sorted(set(author_ids_in_work)), 2):
                    a_idx = id_to_idx[a_id]
                    b_idx = id_to_idx[b_id]
                    graph.add_edge(a_idx, b_idx, {"type": "collaboration"})

    return graph, id_to_idx, external_node_count


def _prune_graph(graph: Any):
    """Prunes isolated nodes (degree 0) from the graph."""
    isolated_nodes = []
    for i in graph.node_indices():
        if graph.in_degree(i) == 0 and graph.out_degree(i) == 0:
            isolated_nodes.append(i)

    if isolated_nodes:
        typer.echo(f"Pruning {len(isolated_nodes)} isolated nodes...")
        graph.remove_nodes_from(isolated_nodes)
        typer.echo(
            f"Graph after pruning: {graph.num_nodes()} nodes, {graph.num_edges()} edges"
        )
    else:
        typer.echo("No isolated nodes found to prune.")




def _calculate_node_sizes(graph: Any, size_by: str) -> Tuple[Dict[int, float], Dict[int, float]]:
    """
    Calculates node sizes based on the selected method.
    
    Returns:
        Tuple containing:
        - Dictionary of node index -> normalized size (for plotting)
        - Dictionary of node index -> raw value (for hover text)
    """
    sizes = {}
    raw_values = {}
    
    if size_by == "centrality":
        # Use Betweenness Centrality as a good measure of importance in citation networks
        typer.echo("Calculating network centrality (betweenness)...")
        raw_values = rx.betweenness_centrality(graph)
        
    elif size_by == "percentile":
        typer.echo("Using citation_normalized_percentile for sizing...")
        for i in graph.node_indices():
            data = graph.get_node_data(i)
            raw_values[i] = data.get("percentile", 0)
    else:
        # Default fixed size
        return {i: 10.0 for i in graph.node_indices()}, {}
        
    # Normalize values to range [5, 30]
    if not raw_values:
        return {i: 10.0 for i in graph.node_indices()}, {}
        
    min_val = min(raw_values.values())
    max_val = max(raw_values.values())
    
    if min_val == max_val:
        return {i: 10.0 for i in graph.node_indices()}, raw_values
        
    for i, val in raw_values.items():
        # Linear normalization: 5 + (val - min) / (max - min) * 25
        normalized = 5 + (val - min_val) / (max_val - min_val) * 25
        sizes[i] = normalized
        
    return sizes, raw_values


def _generate_neo4j_plot(
    graph: Any, 
    source_files: Set[str],
    node_sizes: Dict[int, float],
    raw_metric_values: Dict[int, float] = None
) -> Any:
    """Generates the Neo4j Visualization object from the graph."""
    if raw_metric_values is None:
        raw_metric_values = {}

    import random
    
    # 1. Colors
    source_list = sorted(list(source_files))
    
    # Pre-defined categorical colors loosely mimicking Plotly's default palette
    # Use hex for neo4j_viz
    palette = [
        "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", 
        "#9467bd", "#8c564b", "#e377c2", "#7f7f7f", 
        "#bcbd22", "#17becf"
    ]
    
    source_color_map = {
        src: palette[i % len(palette)] for i, src in enumerate(source_list)
    }
    source_color_map["External"] = "#d62728"
    
    edge_colors = {
        "citation": "#888888",
        "related": "#ff7f0e",
        "authorship": "#2ca02c",
        "affiliation": "#9467bd",
        "collaboration": "#e377c2",
    }
    
    neo4j_nodes = []
    # 2. Add Nodes
    for i in graph.node_indices():
        data = graph.get_node_data(i)
        src = data.get("source_file", "Unknown")
        
        title = data.get("title", "Unknown")
        year = data.get("year", "N/A")
        if data.get("type") in ["author", "institution"]:
            year = "Entity"
        wid = data.get("id", "N/A")
        percentile = data.get("percentile", "N/A")
        
        # Color logic
        color_key = "External" if data.get("type") == "external" else src
        
        if src == "Author":
            color = "#17becf" # Cyan
        elif src == "Institution":
            color = "#bcbd22" # Lime
        else:
            color = source_color_map.get(color_key, "#1f77b4")
            
        # Hover info
        properties = {
            "ID": wid,
            "Year": year,
            "Source": src,
            "Percentile": percentile,
        }
        
        if i in raw_metric_values and raw_metric_values:
            properties["Metric Value"] = f"{raw_metric_values[i]:.4f}"
            
        # Node Size
        # neo4j_viz size scales are a bit different, 10-30 usually works best.
        s = node_sizes.get(i, 10.0)
        
        neo4j_nodes.append(Node(
            id=i,
            size=s,
            caption=str(title)[:30] + '...' if len(str(title)) > 30 else str(title),
            color=color,
            properties=properties
        ))
        
    # 3. Add Edges
    neo4j_rels = []
    for index in graph.edge_indices():
        endpoints = graph.get_edge_endpoints_by_index(index)
        if not endpoints: continue
        u, v = endpoints
        
        data = graph.get_edge_data_by_index(index)
        et = data.get("type", "citation") if data else "citation"
        
        color = edge_colors.get(et, "#888888")
        
        neo4j_rels.append(Relationship(
            source=u,
            target=v,
            caption=et,
            color=color,
        ))

    typer.echo(f"  - Built visualization: {len(neo4j_nodes)} nodes, {len(neo4j_rels)} relationships.")
    
    vg = VisualizationGraph(
        nodes=neo4j_nodes,
        relationships=neo4j_rels
    )
    return vg



network_app = typer.Typer(
    name="network",
    help="Build and visualize citation and entity networks",
    no_args_is_help=True,
)


@network_app.command(name="build")
def build(
    input_path: Annotated[
        Path,
        typer.Option(
            "--input-path",
            "-i",
            help="Path to the works JSONL file or directory containing JSONL files",
            exists=True,
            file_okay=True,
            dir_okay=True,
            readable=True,
        ),
    ],
    output_graphml: Annotated[
        Path,
        typer.Option(
            "--output-graphml",
            "-o",
            help="Path to save the network graph in GraphML format (.graphml)",
        ),
    ] = Path("network.graphml"),
    include_external: Annotated[
        bool,
        typer.Option(
            "--include-external",
            help="Include referenced works not present in the input file (warning: can create large graphs)",
        ),
    ] = False,
    prune: Annotated[
        bool,
        typer.Option(
            "--prune/--no-prune",
            help="Remove isolated nodes (degree 0) from the graph",
        ),
    ] = True,
    edge_types: Annotated[
        List[str],
        typer.Option(
            "--edge-type",
            help="Edge type(s) to build network from: 'citation', 'related', 'authorship', or 'affiliation'",
        ),
    ] = ["citation"],
):
    """
    Builds a citation/entity network from OpenAlex works and saves it to a GraphML file.
    """
    if rx is None:
        typer.echo(
            "Error: rustworkx is required for this command.", err=True
        )
        typer.echo("Please install it with: pip install rustworkx", err=True)
        raise typer.Exit(1)

    # Validate edge types
    valid_types = ["citation", "related", "authorship", "affiliation", "collaboration"]
    for et in edge_types:
        if et not in valid_types:
            typer.echo(f"Error: Invalid edge type '{et}'. Must be one of {valid_types}.", err=True)
            raise typer.Exit(1)

    try:
        # 1. Determine Input Files
        if input_path.is_dir():
            input_files = list(input_path.glob("*.jsonl"))
            if not input_files:
                typer.echo(f"No .jsonl files found in {input_path}", err=True)
                raise typer.Exit(1)
        else:
            input_files = [input_path]

        # 2. Load Works
        works_data, work_source_map, _ = _load_works(input_files)

        # 3. Build Graph
        graph, _, external_node_count = _build_graph(
            works_data, work_source_map, edge_types, include_external
        )

        typer.echo(f"Graph built: {graph.num_nodes()} nodes, {graph.num_edges()} edges")
        if include_external:
            typer.echo(f"  - Source works: {len(works_data)}")
            typer.echo(f"  - External referenced works: {external_node_count}")

        # 4. Prune Graph
        if prune:
            _prune_graph(graph)

        if graph.num_nodes() == 0:
            typer.echo("Graph is empty.")
            return

        # 5. Export GraphML
        try:
            typer.echo(f"Exporting GraphML to {output_graphml}...")
            # We must convert year/percentile to float/int explicitly or rustworkx complains about type stability across writes
            rx.write_graphml(graph, str(output_graphml))
            typer.echo(f"GraphML saved to {output_graphml}")
        except Exception as e:
            typer.echo(f"Error exporting GraphML: {e}", err=True)
            raise typer.Exit(1)

    except Exception as e:
        _handle_cli_exception(e)


@network_app.command(name="visualize")
def visualize(
    input_graphml: Annotated[
        Path,
        typer.Option(
            "--input-graphml",
            "-i",
            help="Path to the GraphML file created by 'network build'",
            exists=True,
            file_okay=True,
            readable=True,
        ),
    ],
    output_html: Annotated[
        Path,
        typer.Option(
            "--output-html",
            "-o",
            help="Path to save the interactive network HTML visualization",
        ),
    ] = Path("network.html"),
    node_size: Annotated[
        str,
        typer.Option(
            "--node-size",
            help="Metric to determine node size: 'none' (fixed), 'centrality' (betweenness), or 'percentile' (citation_normalized_percentile)",
        ),
    ] = "none",
):
    """
    Visualizes a compiled network graph (GraphML) using Neo4j Visualization Library and saves the HTML.
    """
    if rx is None or VisualizationGraph is None:
        typer.echo(
            "Error: rustworkx and neo4j-viz are required for this command.", err=True
        )
        typer.echo("Please install them with: pip install rustworkx neo4j-viz", err=True)
        raise typer.Exit(1)

    try:
        typer.echo(f"Loading GraphML from {input_graphml}...")
        try:
            graphs = rx.read_graphml(str(input_graphml))
            if not graphs:
                typer.echo("Error: No graphs found in the GraphML file.", err=True)
                raise typer.Exit(1)
            graph = graphs[0]
        except Exception as e:
            typer.echo(f"Error loading GraphML: {e}", err=True)
            raise typer.Exit(1)
        
        typer.echo(f"Graph loaded: {graph.num_nodes()} nodes, {graph.num_edges()} edges")
        
        if graph.num_nodes() == 0:
            typer.echo("Graph is empty.")
            return

        # Dynamically determine source files
        source_files_set = set()
        for i in graph.node_indices():
            data = graph.get_node_data(i)
            src_file = data.get("source_file")
            if src_file and src_file != "External":
                source_files_set.add(src_file)
                
        # Calculate node sizes
        node_sizes, raw_metric_values = _calculate_node_sizes(graph, node_size)

        # 2. Generate Plot using neo4j-viz
        typer.echo("Generating interactive visualization using neo4j-viz native physics layout...")
        try:
            vg = _generate_neo4j_plot(
                graph, 
                source_files_set, 
                node_sizes, 
                raw_metric_values
            )
            
            html_output = vg.render(width="100%", height="800px")
            if hasattr(html_output, "data"):
                content = html_output.data
            else:
                content = str(html_output)
                
            with open(output_html, "w", encoding="utf-8") as f:
                f.write(content)
                
            typer.echo(f"Visualization saved to {output_html}")
        except Exception as e:
            typer.echo(f"Visualization failed: {e}")
            raise typer.Exit(1)

    except Exception as e:
        _handle_cli_exception(e)


def create_network_command(app):
    """Create and register the network command suite."""
    app.add_typer(network_app)
