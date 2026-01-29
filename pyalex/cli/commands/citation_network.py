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


def citation_network(
    input_file: Annotated[
        Path,
        typer.Option(
            "--input-file",
            "-i",
            help="Path to the works JSONL file",
            exists=True,
            file_okay=True,
            dir_okay=False,
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
    ] = Path("citation_network.html"),
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

    try:
        graph = rx.PyDiGraph()
        id_to_idx = {}

        # List to hold works to ensure we iterate correctly
        works_data = []

        typer.echo(f"Reading works from {input_file}...")
        with open(input_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    work = json.loads(line)
                    works_data.append(work)
                except json.JSONDecodeError:
                    continue

        typer.echo(f"Loaded {len(works_data)} works.")

        # Pass 1: Add nodes for all works in the file
        for work in works_data:
            work_id = work.get("id")
            if work_id:
                if work_id not in id_to_idx:
                    # Store publication year for layout
                    idx = graph.add_node(
                        {
                            "title": work.get("title"),
                            "id": work_id,
                            "is_source": True,
                            "year": work.get("publication_year", 0),
                        }
                    )
                    id_to_idx[work_id] = idx

        # Pass 2: Add edges and optional external nodes
        edge_count = 0
        external_node_count = 0

        for work in works_data:
            source_id = work.get("id")
            if not source_id:
                continue

            source_idx = id_to_idx[source_id]

            referenced_works = work.get("referenced_works", [])
            for ref_id in referenced_works:
                if ref_id in id_to_idx:
                    # Internal edge
                    target_idx = id_to_idx[ref_id]
                    graph.add_edge(source_idx, target_idx, None)
                    edge_count += 1
                elif include_external:
                    # Add external node
                    if ref_id not in id_to_idx:
                        idx = graph.add_node(
                            {
                                "title": "External Work",
                                "id": ref_id,
                                "is_source": False,
                                "year": 0,  # Unknown year for external
                            }
                        )
                        id_to_idx[ref_id] = idx
                        external_node_count += 1

                    target_idx = id_to_idx[ref_id]
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

            # Create Node Traces
            node_x = []
            node_y = []
            node_text = []
            node_colors = []

            for i in graph.node_indices():
                if i in pos:
                    x, y = pos[i]
                    node_x.append(x)
                    node_y.append(y)

                    data = graph.get_node_data(i)
                    title = data.get("title", "Unknown")
                    year = data.get("year", "N/A")
                    wid = data.get("id", "N/A")

                    # Hover text
                    node_text.append(f"<b>{title}</b><br>Year: {year}<br>ID: {wid}")

                    # Color (Blue for source, Red for external)
                    if data.get("is_source"):
                        node_colors.append("#1f77b4")  # Blue
                    else:
                        node_colors.append("#d62728")  # Red

            node_trace = go.Scatter(
                x=node_x,
                y=node_y,
                mode="markers",
                hoverinfo="text",
                text=node_text,
                marker=dict(color=node_colors, size=10, line_width=2),
            )

            # Create Figure
            fig = go.Figure(
                data=[edge_trace, node_trace],
                layout=go.Layout(
                    title=dict(
                        text=f"<br>Citation Network ({graph.num_nodes()} nodes, {graph.num_edges()} edges)",
                        font=dict(size=16),
                    ),
                    showlegend=False,
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


def create_citation_network_command(app):
    """Create and register the citation-network command."""
    app.command(name="citation-network", rich_help_panel="Utility Commands")(
        citation_network
    )
