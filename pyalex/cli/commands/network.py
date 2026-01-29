"""
Citation network builder command for PyAlex CLI.

This command builds a citation network from OpenAlex works using rustworkx and visualizes it with Plotly.
"""

import json
from pathlib import Path
from typing import Annotated

import typer

try:
    import rustworkx as rx
    import plotly.graph_objects as go
except ImportError:
    rx = None
    go = None

from ..utils import _handle_cli_exception


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
    edge_type: Annotated[
        str,
        typer.Option(
            "--edge-type",
            help="Edge type to build network from: 'citation' (referenced_works) or 'related' (related_works)",
        ),
    ] = "citation",
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

    if edge_type not in ["citation", "related"]:
        typer.echo("Error: --edge-type must be either 'citation' or 'related'.", err=True)
        raise typer.Exit(1)

    try:
        graph = rx.PyDiGraph()
        id_to_idx = {}

        # Determine input files
        if input_path.is_dir():
            input_files = list(input_path.glob("*.jsonl"))
            if not input_files:
                typer.echo(f"No .jsonl files found in {input_path}", err=True)
                raise typer.Exit(1)
        else:
            input_files = [input_path]

        # List to hold works to ensure we iterate correctly
        works_data = []
        # Mapping from work ID to source filename (stem)
        work_source_map = {}
        source_files = set()

        for file_path in input_files:
            source_name = file_path.name
            source_files.add(source_name)
            typer.echo(f"Reading works from {file_path}...")
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

        # Pass 1: Add nodes for all works in the file
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

        # Pass 2: Add edges and optional external nodes
        edge_count = 0
        external_node_count = 0

        edge_field = "referenced_works" if edge_type == "citation" else "related_works"
        typer.echo(f"Building {edge_type} network using field '{edge_field}'...")

        for work in works_data:
            source_id = work.get("id")
            if not source_id:
                continue

            source_id = source_id.replace("https://openalex.org/", "")
            source_idx = id_to_idx[source_id]

            targets = work.get(edge_field, [])
            for target_ref in targets:
                # Clean ID if it's a URL
                target_id = target_ref.replace("https://openalex.org/", "")
                
                if target_id in id_to_idx:
                    # Internal edge
                    target_idx = id_to_idx[target_id]
                    # Avoid self-loops if related works point back to self (unlikely but possible)
                    if source_idx != target_idx:
                        graph.add_edge(source_idx, target_idx, None)
                        edge_count += 1
                elif include_external:
                    # Add external node
                    if target_id not in id_to_idx:
                        idx = graph.add_node(
                            {
                                "title": "External Work",
                                "id": target_id,
                                "type": "external",
                                "source_file": "External",
                                "year": 0,  # Unknown year for external
                            }
                        )
                        id_to_idx[target_id] = idx
                        external_node_count += 1

                    target_idx = id_to_idx[target_id]
                    graph.add_edge(source_idx, target_idx, None)
                    edge_count += 1

        typer.echo(f"Graph built: {graph.num_nodes()} nodes, {graph.num_edges()} edges")
        if include_external:
            typer.echo(f"  - Source works: {len(works_data)}")
            typer.echo(f"  - External referenced works: {external_node_count}")

        if prune:
            # Find isolated nodes (in_degree == 0 AND out_degree == 0)
            # Note: In a directed graph, we check both.
            isolated_nodes = []
            for i in graph.node_indices():
                if graph.in_degree(i) == 0 and graph.out_degree(i) == 0:
                    isolated_nodes.append(i)

            if isolated_nodes:
                typer.echo(f"Pruning {len(isolated_nodes)} isolated nodes...")
                graph.remove_nodes_from(isolated_nodes)
                # Rebuild indices mapping if needed, but for visualization we iterate nodes directly
                typer.echo(
                    f"Graph after pruning: {graph.num_nodes()} nodes, {graph.num_edges()} edges"
                )
            else:
                typer.echo("No isolated nodes found to prune.")

        if graph.num_nodes() == 0:
            typer.echo("Graph is empty.")
            return

        # Visualization
        typer.echo(f"Generating interactive visualization using '{layout}' layout...")

        try:
            # Calculate Positions
            if layout == "time-shell":
                years = {}
                for i in graph.node_indices():
                    data = graph.get_node_data(i)
                    y = data.get("year")
                    if y is None:
                        y = 0
                    if y not in years:
                        years[y] = []
                    years[y].append(i)

                sorted_years = sorted(years.keys())
                shells = [years[y] for y in sorted_years]
                typer.echo(
                    f"  - Organized into {len(shells)} time shells: {sorted_years}"
                )
                pos = rx.shell_layout(graph, nlist=shells)
            elif layout == "timeline":
                years = {}
                for i in graph.node_indices():
                    data = graph.get_node_data(i)
                    y = data.get("year")
                    if y is None or y == 0:
                        y = 0
                    if y not in years:
                        years[y] = []
                    years[y].append(i)

                # Handle unknown years (0)
                known_years = [y for y in years.keys() if y != 0]
                if known_years:
                    min_year = min(known_years)
                    if 0 in years:
                        years[min_year - 1] = years.pop(0)
                elif 0 in years:
                    # Only unknown years
                    pass

                pos = {}
                # Sort years to ensure consistent timeline layout
                for year in sorted(years.keys()):
                    nodes = years[year]
                    # Sort nodes alphabetically within the year
                    nodes.sort(
                        key=lambda n: graph.get_node_data(n).get("title", "") or ""
                    )
                    n = len(nodes)
                    for idx, node_idx in enumerate(nodes):
                        # Vertical spread centered at 0
                        y_pos = idx - (n - 1) / 2.0
                        pos[node_idx] = (year, y_pos)

                if years:
                    typer.echo(
                        f"  - Organized chronologically from {min(years.keys())} to {max(years.keys())}"
                    )
                else:
                    typer.echo("  - No year data available for timeline layout.")

            else:
                # Default spring
                pos = rx.spring_layout(
                    graph, k=2.0 / (graph.num_nodes() ** 0.5 + 1)
                )  # avoid div by zero

            # Create Edge Traces
            edge_x = []
            edge_y = []
            for edge in graph.edge_list():
                if edge[0] in pos and edge[1] in pos:
                    x0, y0 = pos[edge[0]]
                    x1, y1 = pos[edge[1]]
                    edge_x.extend([x0, x1, None])
                    edge_y.extend([y0, y1, None])

            edge_trace = go.Scatter(
                x=edge_x,
                y=edge_y,
                line=dict(width=0.5, color="#888"),
                hoverinfo="none",
                mode="lines",
            )

            # Assign colors based on source file
            # Define a color palette
            # Using Plotly's default qualitative sequence
            import plotly.colors as pcolors

            palette = pcolors.qualitative.Plotly
            source_list = sorted(list(source_files))
            source_color_map = {
                src: palette[i % len(palette)] for i, src in enumerate(source_list)
            }
            source_color_map["External"] = "#d62728"  # Explicit Red for External

            # Create one trace per group (source file) + External
            # This allows the legend to show source files
            traces = [edge_trace]

            # Group nodes by their source_file
            nodes_by_source = {}
            # Initialize with all keys including External (if present)
            # Actually better to just iterate:
            
            # Helper to organize node data
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
                    if data.get("type") == "external":
                        c = source_color_map.get("External", "#d62728")
                    else:
                        c = source_color_map.get(src, "#1f77b4")
                    nodes_by_source[src]["color"].append(c)

            # Create scatter traces for each group
            # Sort keys to ensure consistent legend order. Put 'External' last.
            sorted_sources = sorted([s for s in nodes_by_source.keys() if s != "External"])
            if "External" in nodes_by_source:
                sorted_sources.append("External")
                
            for src in sorted_sources:
                group_data = nodes_by_source[src]
                # Use a single color for the trace if they are all the same, or individual
                # Actually, best to just set the color for the whole trace based on mapping
                if src == "External":
                    color = source_color_map.get("External", "#d62728")
                else:
                    color = source_color_map.get(src, "#888888") # Fallback

                node_trace = go.Scatter(
                    x=group_data["x"],
                    y=group_data["y"],
                    mode="markers",
                    name=src, # Legend name
                    hoverinfo="text",
                    text=group_data["text"],
                    marker=dict(color=color, size=10, line_width=2),
                )
                traces.append(node_trace)

            # Create Figure
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
                        title=dict(text="Publication Year")
                        if layout == "timeline"
                        else None,
                        showgrid=True if layout == "timeline" else False,
                        zeroline=False,
                        showticklabels=True if layout == "timeline" else False,
                    ),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                ),
            )
            
            fig.write_html(str(output_html))
            typer.echo(f"Visualization saved to {output_html}")

        except Exception as e:
            typer.echo(f"Visualization failed: {e}")
            raise typer.Exit(1)

    except Exception as e:
        _handle_cli_exception(e)


def create_network_command(app):
    """Create and register the network command."""
    app.command(name="network", rich_help_panel="Utility Commands")(
        network
    )
