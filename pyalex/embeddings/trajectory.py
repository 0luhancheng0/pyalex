"""Compute semantic trajectories for authors over time and save as PNG.

This module takes a network graph and embeddings, calculates yearly 
aggregated embeddings for authors, and projects them onto 3 selected 
topics to visualize research focus evolution via ternary coordinates.
"""

import json
import logging
from pathlib import Path
from typing import Annotated, Optional

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import typer

from pyalex.embeddings.data_loader import load_graphml_to_rx

try:
    from pyalex.logger import get_logger
    logger = get_logger()
except ImportError:
    logger = logging.getLogger(__name__)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def softmax(x: np.ndarray, tau: float = 1.0) -> np.ndarray:
    """Compute softmax values for each sets of scores in x with temperature tau."""
    e_x = np.exp((x - np.max(x)) / tau)
    return e_x / e_x.sum()


def trajectory(
    graphml: Annotated[
        Path,
        typer.Argument(
            help="Path to the GraphML file produced by `pyalex network build`.",
            exists=True,
            file_okay=True,
            readable=True,
        ),
    ],
    parquet: Annotated[
        Path,
        typer.Argument(
            help="Path to the embeddings Parquet file produced by `pyalex embedding generate`.",
            exists=True,
            file_okay=True,
            readable=True,
        ),
    ],
    topic_ids: Annotated[
        str,
        typer.Option(
            "--topic-ids",
            "-t",
            help="Comma-separated list of exactly 3 topic IDs (e.g. T10036,T12697,T12006) defining the ternary space.",
        ),
    ],
    output_image: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Path to save the trajectory PNG plot.",
        ),
    ] = Path("trajectory.png"),
    output_json: Annotated[
        Optional[Path],
        typer.Option(
            "--output-json",
            help="Path to save the trajectory raw JSON data (optional).",
        ),
    ] = None,
    author_ids: Annotated[
        Optional[str],
        typer.Option(
            "--author-ids",
            help="Comma-separated list of author IDs to analyze. If omitted, analyzes all authors in the graph.",
        ),
    ] = None,
    tau: Annotated[
        float,
        typer.Option(
            "--tau",
            help="Temperature for softmax projection. Smaller values make the projection more 'peaky'.",
        ),
    ] = 0.05,
    min_works_per_year: Annotated[
        int,
        typer.Option(
            "--min-works",
            help="Minimum number of works an author must have in a year to include that year in the trajectory.",
        ),
    ] = 1,
    width: Annotated[
        int,
        typer.Option(
            "--width",
            help="Width of the output image in pixels.",
        ),
    ] = 1200,
    height: Annotated[
        int,
        typer.Option(
            "--height",
            help="Height of the output image in pixels.",
        ),
    ] = 900,
):
    """Compute author semantic trajectories and save the visualization to a PNG.

    Projects yearly author embeddings into a ternary space defined by 3 topics.
    Outputs a PNG image showing the research evolution of authors over time.
    """
    # 1. Parse topic IDs
    t_ids = [tid.strip() for tid in topic_ids.split(",")]
    if len(t_ids) != 3:
        typer.echo("Error: Exactly 3 topic IDs are required for ternary projection.", err=True)
        raise typer.Exit(1)

    # 2. Load Graph
    typer.echo(f"Loading graph from {graphml}...")
    graph = load_graphml_to_rx(str(graphml))
    typer.echo(f"Graph loaded with {graph.num_nodes()} nodes.")

    # 3. Load Embeddings
    typer.echo(f"Loading embeddings from {parquet}...")
    df = pd.read_parquet(parquet)

    # Create id -> embedding map
    id_to_emb = {}
    for _, row in df.iterrows():
        id_to_emb[row["id"]] = np.array(row["embedding"], dtype=np.float32)

    # 4. Get Topic Embeddings
    topic_embs = []
    topic_names = []
    for tid in t_ids:
        if tid not in id_to_emb:
            typer.echo(f"Error: Topic {tid} not found in embeddings file.", err=True)
            raise typer.Exit(1)
        topic_embs.append(id_to_emb[tid])
        
        # Try to find name in graph
        name = tid
        for idx in graph.node_indices():
            data = graph.get_node_data(idx)
            if data.get("id") == tid:
                name = data.get("title") or data.get("display_name") or tid
                break
        topic_names.append(name)

    # 5. Determine authors to analyze
    target_author_ids = [aid.strip() for aid in author_ids.split(",")] if author_ids else []

    # Filter author nodes in graph
    author_nodes = []
    for idx in graph.node_indices():
        data = graph.get_node_data(idx)
        if data.get("type") == "author":
            a_id = data.get("id")
            if not target_author_ids or a_id in target_author_ids:
                name = data.get("title") or data.get("display_name") or "Unknown Author"
                author_nodes.append((idx, a_id, name))

    if not author_nodes:
        typer.echo("No matching authors found in the graph.")
        return

    typer.echo(f"Computing trajectories for {len(author_nodes)} authors...")
    results = []

    # 6. Compute trajectories
    for a_node_idx, a_id, a_name in author_nodes:
        work_indices = graph.predecessor_indices(a_node_idx)

        yearly_works = {}
        for w_idx in work_indices:
            w_data = graph.get_node_data(w_idx)
            w_id = w_data.get("id")
            
            # Use data from graph nodes (year is stored there)
            year_val = w_data.get("year")
            
            if not year_val or w_id not in id_to_emb:
                continue
            
            try:
                year = int(year_val)
                if year == 0:
                    continue
            except (ValueError, TypeError):
                continue

            yearly_works.setdefault(year, []).append(id_to_emb[w_id])

        if not yearly_works:
            continue

        author_trajectory = []
        for year in sorted(yearly_works.keys()):
            works = yearly_works[year]
            if len(works) < min_works_per_year:
                continue

            # Compute mean embedding for the year
            year_emb = np.mean(works, axis=0).astype(np.float32)

            # Cosine similarity to each topic
            similarities = np.array([cosine_similarity(year_emb, te) for te in topic_embs])
            
            # Project onto ternary coordinates using softmax
            coords = softmax(similarities, tau=tau).tolist()

            author_trajectory.append({
                "year": year,
                "coordinates": coords,
                "n_works": len(works),
                "similarities": similarities.tolist(),
            })

        if author_trajectory:
            results.append({
                "author_id": a_id,
                "author_name": a_name,
                "trajectory": author_trajectory,
            })

    if not results:
        typer.echo("No trajectory data computed.")
        return

    # 7. Save JSON if requested
    if output_json:
        output_json.parent.mkdir(parents=True, exist_ok=True)
        with open(output_json, "w") as f:
            json.dump(
                {
                    "topic_ids": t_ids,
                    "topic_names": topic_names,
                    "tau": tau,
                    "authors": results,
                },
                f,
                indent=2,
            )
        typer.echo(f"Saved raw data to {output_json}")

    # 8. Create Plotly figure
    rows = []
    for author in results:
        name = author["author_name"]
        for point in author["trajectory"]:
            coords = point["coordinates"]
            rows.append({
                "author": name,
                "year": point["year"],
                "n_works": point["n_works"],
                "topic_a": coords[0],
                "topic_b": coords[1],
                "topic_c": coords[2],
            })

    plot_df = pd.DataFrame(rows).sort_values(["author", "year"])

    # Create ternary scatter plot
    fig = px.scatter_ternary(
        plot_df,
        a="topic_a",
        b="topic_b",
        c="topic_c",
        color="author",
        size="n_works",
        hover_name="author",
        hover_data={"year": True, "n_works": True, "topic_a": ":.2f", "topic_b": ":.2f", "topic_c": ":.2f"},
        labels={
            "topic_a": topic_names[0],
            "topic_b": topic_names[1],
            "topic_c": topic_names[2],
        },
        title=f"Author Semantic Trajectories (τ={tau})",
    )

    # Add lines between points for each author
    for author_name in plot_df["author"].unique():
        author_df = plot_df[plot_df["author"] == author_name]
        if len(author_df) > 1:
            fig.add_trace(
                go.Scatterternary(
                    a=author_df["topic_a"],
                    b=author_df["topic_b"],
                    c=author_df["topic_c"],
                    mode="lines",
                    line=dict(width=1),
                    showlegend=False,
                    hoverinfo="skip",
                    marker=dict(size=0),
                    opacity=0.3,
                )
            )

    # 9. Save PNG
    output_image.parent.mkdir(parents=True, exist_ok=True)
    try:
        fig.write_image(str(output_image), width=width, height=height)
        typer.echo(f"Success! Saved trajectory plot to {output_image}")
    except Exception as e:
        typer.echo(f"Error saving PNG: {e}", err=True)
        typer.echo("Note: Saving static images in Plotly requires the 'kaleido' package. Try: pip install kaleido")
        # Try saving as HTML as a fallback? No, let's just fail or suggest the fix.
        raise typer.Exit(1)
