"""
Citation network builder command for PyAlex CLI.

This command builds a citation network from OpenAlex works using rustworkx and visualizes it with Plotly.
"""

import json
from pathlib import Path
from typing import Annotated, List, Dict, Set, Any, Tuple

import typer

try:
    import rustworkx as rx
    import plotly.graph_objects as go
    import plotly.colors as pcolors
except ImportError:
    rx = None
    go = None
    pcolors = None

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
                # Use original ID for map lookup as work_source_map uses original IDs
                source_name = work_source_map.get(work.get("id"), "Unknown")
                
                # Store publication year for layout
                idx = graph.add_node(
                    {
                        "title": work.get("title"),
                        "id": work_id,
                        "type": "source",
                        "source_file": source_name,
                        "year": work.get("publication_year", 0),
                    }
                )
                id_to_idx[work_id] = idx

    external_node_count = 0

    # Pass 2: Add edges
    for et in edge_types:
        edge_field = "referenced_works" if et == "citation" else "related_works"
        typer.echo(f"Adding '{et}' edges from field '{edge_field}'...")

        for work in works_data:
            source_id = work.get("id")
            if not source_id:
                continue

            source_id = source_id.replace("https://openalex.org/", "")
            # Ensure source exists in graph (it should from Pass 1)
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
                            }
                        )
                        id_to_idx[target_id] = idx
                        external_node_count += 1

                    target_idx = id_to_idx[target_id]
                    graph.add_edge(source_idx, target_idx, {"type": et})
    
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


def _calculate_layout(graph: Any, layout: str) -> Dict[int, Tuple[float, float]]:
    """Calculates node positions based on the selected layout algorithm."""
    
    if layout == "time-shell":
        years = {}
        for i in graph.node_indices():
            data = graph.get_node_data(i)
            y = data.get("year", 0) or 0
            if y not in years: years[y] = []
            years[y].append(i)

        sorted_years = sorted(years.keys())
        shells = [years[y] for y in sorted_years]
        typer.echo(f"  - Organized into {len(shells)} time shells: {sorted_years}")
        return rx.shell_layout(graph, nlist=shells)

    elif layout == "timeline":
        years = {}
        for i in graph.node_indices():
            data = graph.get_node_data(i)
            y = data.get("year", 0) or 0
            if y not in years: years[y] = []
            years[y].append(i)

        # Handle unknown years (0) - put them before min year
        known_years = [y for y in years.keys() if y != 0]
        if known_years:
            min_year = min(known_years)
            if 0 in years:
                years[min_year - 1] = years.pop(0)
        
        pos = {}
        if years:
             typer.echo(f"  - Organized chronologically from {min(years.keys())} to {max(years.keys())}")  
             
        for year in sorted(years.keys()):
            nodes = years[year]
            nodes.sort(key=lambda n: graph.get_node_data(n).get("title", "") or "")
            n = len(nodes)
            for idx, node_idx in enumerate(nodes):
                y_pos = idx - (n - 1) / 2.0
                pos[node_idx] = (year, y_pos)
        return pos
    
    else: # Default: spring
        # simple spring layout
        return rx.spring_layout(graph, k=2.0 / (graph.num_nodes() ** 0.5 + 1))


def _generate_plot(
    graph: Any, 
    pos: Dict[int, Tuple[float, float]], 
    edge_types: List[str], 
    source_files: Set[str],
    layout: str
) -> go.Figure:
    """Generates the Plotly figure from the graph and positions."""
    traces = []
    
    # 1. Edge Traces
    edge_colors = {
        "citation": "#888888",  # Gray
        "related": "#ff7f0e",   # Orange
    }
    
    # Pre-aggregate coordinates by type to avoid creating too many small traces
    type_edge_coords = {et: {"x": [], "y": []} for et in edge_types}
    
    for index in graph.edge_indices():
        endpoints = graph.get_edge_endpoints_by_index(index)
        if not endpoints: continue
        u, v = endpoints
        
        if u in pos and v in pos:
            data = graph.get_edge_data_by_index(index)
            et = data.get("type", "citation") if data else "citation"
            
            if et in type_edge_coords:
                x0, y0 = pos[u]
                x1, y1 = pos[v]
                type_edge_coords[et]["x"].extend([x0, x1, None])
                type_edge_coords[et]["y"].extend([y0, y1, None])

    for et in edge_types:
        coords = type_edge_coords[et]
        if not coords["x"]:
            continue
            
        color = edge_colors.get(et, "#888")
        
        traces.append(go.Scatter(
            x=coords["x"],
            y=coords["y"],
            line=dict(width=0.5, color=color),
            hoverinfo="none",
            mode="lines",
            name=f"Edges: {et}",
            opacity=0.5
        ))

    # 2. Node Traces (grouped by source file)
    # Define a color palette
    palette = pcolors.qualitative.Plotly
    source_list = sorted(list(source_files))
    source_color_map = {
        src: palette[i % len(palette)] for i, src in enumerate(source_list)
    }
    source_color_map["External"] = "#d62728"  # Explicit Red for External

    nodes_by_source = {}
    
    for i in graph.node_indices():
        if i in pos:
            data = graph.get_node_data(i)
            src = data.get("source_file", "Unknown")
            if src not in nodes_by_source:
                nodes_by_source[src] = {"x": [], "y": [], "text": [], "color": []}
            
            x, y = pos[i]
            nodes_by_source[src]["x"].append(x)
            nodes_by_source[src]["y"].append(y)
            
            title = data.get("title", "Unknown")
            year = data.get("year", "N/A")
            wid = data.get("id", "N/A")
            
            nodes_by_source[src]["text"].append(f"<b>{title}</b><br>Year: {year}<br>ID: {wid}<br>Source: {src}")
            
            # Color logic
            color_key = "External" if data.get("type") == "external" else src
            c = source_color_map.get(color_key, "#1f77b4")
            nodes_by_source[src]["color"].append(c)

    # Sort sources for consistent legend
    sorted_sources = sorted([s for s in nodes_by_source.keys() if s != "External"])
    if "External" in nodes_by_source:
        sorted_sources.append("External")
        
    for src in sorted_sources:
        group_data = nodes_by_source[src]
        color = source_color_map.get("External" if src == "External" else src, "#888")
        
        traces.append(go.Scatter(
            x=group_data["x"],
            y=group_data["y"],
            mode="markers",
            name=src, 
            hoverinfo="text",
            text=group_data["text"],
            marker=dict(color=color, size=10, line_width=2),
        ))

    # 3. Create Figure
    fig = go.Figure(
        data=traces,
        layout=go.Layout(
            title=dict(
                text=f"<br>Citation Network ({graph.num_nodes()} nodes, {graph.num_edges()} edges)",
                font=dict(size=16),
            ),
            showlegend=True,
            hovermode="closest",
            margin=dict(b=60, l=5, r=5, t=40),
            annotations=[
                dict(
                    text=f"Layout: {layout}",
                    showarrow=False,
                    xref="paper",
                    yref="paper",
                    x=0.005,
                    y=-0.002,
                )
            ],
            xaxis=dict(
                title=dict(text="Publication Year") if layout == "timeline" else None,
                showgrid=True if layout == "timeline" else False,
                zeroline=False,
                showticklabels=True if layout == "timeline" else False,
            ),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        ),
    )
    return fig


def network(
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
    output_html: Annotated[
        Path,
        typer.Option(
            "--output-html",
            "-o",
            help="Path to save the interactive network visualization",
        ),
    ] = Path("network.html"),
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
    layout: Annotated[
        str,
        typer.Option(
            "--layout",
            help="Layout algorithm: 'spring', 'time-shell' (concentric), or 'timeline' (default, chronological x-axis)",
        ),
    ] = "timeline",
    edge_types: Annotated[
        List[str],
        typer.Option(
            "--edge-type",
            help="Edge type(s) to build network from: 'citation' (referenced_works) or 'related' (related_works)",
        ),
    ] = ["citation"],
):
    """
    Builds a citation network from OpenAlex works using rustworkx and visualizes it with Plotly.
    """
    if rx is None or go is None:
        typer.echo(
            "Error: rustworkx and plotly are required for this command.", err=True
        )
        typer.echo("Please install them with: pip install rustworkx plotly", err=True)
        raise typer.Exit(1)

    # Validate edge types
    valid_types = ["citation", "related"]
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
        works_data, work_source_map, source_files = _load_works(input_files)

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

        # 5. Calculate Layout
        typer.echo(f"Generating interactive visualization using '{layout}' layout...")
        pos = _calculate_layout(graph, layout)

        # 6. Generate Plot
        try:
            fig = _generate_plot(graph, pos, edge_types, source_files, layout)
            fig.write_html(str(output_html))
            typer.echo(f"Visualization saved to {output_html}")
        except Exception as e:
            typer.echo(f"Visualization failed: {e}")
            raise typer.Exit(1)

    except Exception as e:
        _handle_cli_exception(e)


def create_network_command(app):
    """Create and register the network command."""
    app.command(name="network", rich_help_panel=VISUALIZATION_PANEL)(
        network
    )
