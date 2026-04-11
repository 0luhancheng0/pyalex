"""Embedding generation utility for OpenAlex entity graphs.

Generates embeddings for all entity types in a GraphML network file:
- Works: text embeddings from title + abstract
- Authors: average of their connected works' embeddings
- Topics: average of their connected works' embeddings
- Institutions: average of their connected authors' embeddings

The output is a Parquet file per entity type, directly compatible with
the `embedding-atlas` CLI for interactive visualisation.
"""

import functools
import json
import logging
from pathlib import Path
from typing import Annotated, Optional

import numpy as np
import pandas as pd
import rustworkx as rx
import typer

from .data_loader import load_graphml_to_rx
from .trajectory import trajectory as trajectory_command

try:
    from ..logger import get_logger

    logger = get_logger()
except ImportError:
    logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Model helpers
# ---------------------------------------------------------------------------


@functools.lru_cache(maxsize=2)
def _get_model(model_name: str):
    """Lazily load and cache the SentenceTransformer model."""
    from sentence_transformers import SentenceTransformer

    logger.info(f"Loading embedding model: {model_name}")
    return SentenceTransformer(model_name)


def generate_embeddings(
    texts: list[str], model_name: str = "all-MiniLM-L6-v2", batch_size: int = 32
) -> list[Optional[list[float]]]:
    """Generate embeddings for a list of texts using the specified model.

    Parameters
    ----------
    texts : list[str]
        A list of strings to be embedded.
    model_name : str, optional
        The name of the sentence-transformers model to use.
    batch_size : int, optional
        Batch size, default 32.

    Returns
    -------
    list[Optional[list[float]]]
        A list of embedding vectors (or None for empty inputs).
    """
    if not texts:
        return []

    model = _get_model(model_name)

    valid_texts_idx = []
    valid_texts = []

    for i, t in enumerate(texts):
        if t and isinstance(t, str) and t.strip():
            valid_texts_idx.append(i)
            valid_texts.append(t.strip())

    embeddings_list: list[Optional[list[float]]] = [None] * len(texts)

    if valid_texts:
        embs = model.encode(valid_texts, batch_size=batch_size, show_progress_bar=False)
        embs_list = embs.tolist()

        for idx, row in zip(valid_texts_idx, embs_list):
            embeddings_list[idx] = row

    return embeddings_list


# ---------------------------------------------------------------------------
# Graph-aware embedding strategies
# ---------------------------------------------------------------------------


def _parse_int_or_none(value) -> Optional[int]:
    """Parse integer-like values from GraphML attributes.

    Returns None if parsing fails.
    """
    if value is None:
        return None
    try:
        if isinstance(value, str):
            value = value.split(".")[0]
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _embed_works(
    graph: rx.PyDiGraph,
    node_type_map: dict[str, list[int]],
    model_name: str = "all-MiniLM-L6-v2",
    batch_size: int = 32,
) -> dict[int, np.ndarray]:
    """Generate text embeddings for work nodes from title + abstract."""
    work_indices = node_type_map.get("source", [])
    if not work_indices:
        typer.echo("  No work nodes found in the graph.")
        return {}

    texts = []
    for idx in work_indices:
        attrs = graph.get_node_data(idx)
        title = attrs.get("title", "") or ""
        abstract = attrs.get("abstract", "") or ""
        texts.append(f"{title} {abstract}".strip())

    typer.echo(f"  Generating text embeddings for {len(work_indices)} works...")
    raw_embeddings = generate_embeddings(texts, model_name=model_name, batch_size=batch_size)

    result: dict[int, np.ndarray] = {}
    for node_idx, emb in zip(work_indices, raw_embeddings):
        if emb is not None:
            result[node_idx] = np.array(emb, dtype=np.float32)
    return result


def _embed_authors(
    graph: rx.PyDiGraph,
    node_type_map: dict[str, list[int]],
    work_embeddings: dict[int, np.ndarray],
) -> dict[int, np.ndarray]:
    """Compute author embeddings from connected work embeddings.

    Only works present in *work_embeddings* (i.e. those that exist in the
    input graph and received a valid embedding) are considered.
    """
    author_indices = node_type_map.get("author", [])
    if not author_indices:
        typer.echo("  No author nodes found in the graph.")
        return {}

    result: dict[int, np.ndarray] = {}

    for author_idx in author_indices:
        # Edges are  work -> author  so we look at predecessors of the author node
        neighbour_embs: list[np.ndarray] = []

        for work_idx in graph.predecessor_indices(author_idx):
            if work_idx in work_embeddings:
                neighbour_embs.append(work_embeddings[work_idx])

        if neighbour_embs:
            result[author_idx] = np.mean(neighbour_embs, axis=0).astype(np.float32)

    typer.echo(
        f"  Computed embeddings for {len(result)}/{len(author_indices)} authors "
        f"(skipped {len(author_indices) - len(result)} without embedded works)."
    )
    return result


def _embed_topics(
    graph: rx.PyDiGraph,
    node_type_map: dict[str, list[int]],
    work_embeddings: dict[int, np.ndarray],
) -> dict[int, np.ndarray]:
    """Compute topic embeddings as the mean of connected work embeddings.

    Only works present in *work_embeddings* are considered.
    """
    topic_indices = node_type_map.get("topic", [])
    if not topic_indices:
        # Don't echo if no topics, as they might not be requested/present
        return {}

    result: dict[int, np.ndarray] = {}
    for topic_idx in topic_indices:
        # Edges are Work -> Topic (similar to Work -> Author)
        predecessor_indices = graph.predecessor_indices(topic_idx)
        neighbour_embs = [
            work_embeddings[p] for p in predecessor_indices if p in work_embeddings
        ]
        if neighbour_embs:
            result[topic_idx] = np.mean(neighbour_embs, axis=0).astype(np.float32)

    typer.echo(
        f"  Computed embeddings for {len(result)}/{len(topic_indices)} topics "
        f"(skipped {len(topic_indices) - len(result)} without embedded works)."
    )
    return result


def _embed_institutions(
    graph: rx.PyDiGraph,
    node_type_map: dict[str, list[int]],
    author_embeddings: dict[int, np.ndarray],
) -> dict[int, np.ndarray]:
    """Compute institution embeddings as the mean of connected author embeddings.

    Only authors present in *author_embeddings* are considered.
    """
    inst_indices = node_type_map.get("institution", [])
    if not inst_indices:
        typer.echo("  No institution nodes found in the graph.")
        return {}

    result: dict[int, np.ndarray] = {}
    for inst_idx in inst_indices:
        # Edges are  author -> institution  so predecessors are authors
        predecessor_indices = graph.predecessor_indices(inst_idx)
        neighbour_embs = [
            author_embeddings[p] for p in predecessor_indices if p in author_embeddings
        ]
        if neighbour_embs:
            result[inst_idx] = np.mean(neighbour_embs, axis=0).astype(np.float32)

    typer.echo(
        f"  Computed embeddings for {len(result)}/{len(inst_indices)} institutions "
        f"(skipped {len(inst_indices) - len(result)} without embedded authors)."
    )
    return result


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def _save_to_parquet(entities: list[dict], output_file: Path):
    """Save a list of entity dicts to a Parquet file, flattening nested fields."""
    if not entities:
        return
    df = pd.DataFrame(entities)
    # Flatten complex nested fields for embedding-atlas compatibility
    for col in df.columns:
        if col != "embedding":
            mask = df[col].apply(lambda x: isinstance(x, (list, dict)))
            if mask.any():
                df.loc[mask, col] = df.loc[mask, col].apply(json.dumps)
    df.to_parquet(output_file, index=False)


def _collect_entities(
    graph: rx.PyDiGraph,
    node_indices: list[int],
    embeddings: dict[int, np.ndarray],
    entity_type: str,
) -> list[dict]:
    """Build a list of entity dicts (with embedding and entity_type) for the given node indices."""
    entities = []
    for idx in node_indices:
        if idx not in embeddings:
            continue
        attrs = (graph.get_node_data(idx) or {}).copy()
        attrs["embedding"] = embeddings[idx].tolist()
        attrs["entity_type"] = entity_type
        entities.append(attrs)
    return entities


def _compute_umap_coordinates(
    entities: list[dict],
    n_neighbors: int = 15,
    min_dist: Optional[float] = None,
    metric: str = "cosine",
    random_state: Optional[int] = None,
) -> None:
    """Compute in-place 2D UMAP coordinates for entities.

    Adds two keys to each entity dict:
    - ``projection_x``
    - ``projection_y``
    """
    if not entities:
        return

    valid_entities = [e for e in entities if isinstance(e.get("embedding"), list) and e["embedding"]]
    if not valid_entities:
        return

    if len(valid_entities) == 1:
        valid_entities[0]["projection_x"] = 0.0
        valid_entities[0]["projection_y"] = 0.0
        return

    vectors = np.array([e["embedding"] for e in valid_entities], dtype=np.float32)

    effective_n_neighbors = min(max(n_neighbors, 2), max(len(valid_entities) - 1, 2))

    umap_kwargs = {
        "n_neighbors": effective_n_neighbors,
        "metric": metric,
        "n_components": 2,
        "random_state": random_state,
    }
    if min_dist is not None:
        umap_kwargs["min_dist"] = min_dist

    import umap

    reducer = umap.UMAP(**umap_kwargs)
    projection = reducer.fit_transform(vectors)

    for entity, coord in zip(valid_entities, projection):
        entity["projection_x"] = float(coord[0])
        entity["projection_y"] = float(coord[1])


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

app = typer.Typer(
    name="embedding",
    help="Generate embeddings for all entity types in an OpenAlex network graph.",
    no_args_is_help=True,
)


@app.command()
def generate(
    input_graphml: Annotated[
        Path,
        typer.Argument(
            help="Path to the GraphML file produced by `pyalex network build`.",
            exists=True,
            file_okay=True,
            readable=True,
        ),
    ],
    output_file: Annotated[
        Path,
        typer.Argument(
            help="Path to write the output Parquet file.",
        ),
    ],
    model: Annotated[
        str,
        typer.Option("--model", "-m", help="SentenceTransformer model name for work embeddings."),
    ] = "all-MiniLM-L6-v2",
    batch_size: Annotated[
        int,
        typer.Option("--batch-size", "-b", help="Batch size for embedding generation."),
    ] = 32,
    umap_n_neighbors: Annotated[
        int,
        typer.Option(
            "--umap-n-neighbors",
            help="Number of neighbors to consider for UMAP dimensionality reduction.",
        ),
    ] = 15,
    umap_min_dist: Annotated[
        Optional[float],
        typer.Option("--umap-min-dist", help="The min_dist parameter for UMAP."),
    ] = None,
    umap_metric: Annotated[
        str,
        typer.Option("--umap-metric", help="Distance metric for UMAP computation."),
    ] = "cosine",
    umap_random_state: Annotated[
        Optional[int],
        typer.Option("--umap-random-state", help="Random seed for reproducible UMAP results."),
    ] = None,
):
    """Generate embeddings for works, authors, and institutions in a network graph.

    Strategy per entity type:
    - **Works**: text embedding from title + abstract via SentenceTransformer.
    - **Authors**: mean aggregation over connected works' embeddings.
    - **Topics**: mean of their connected works' embeddings.
    - **Institutions**: mean of their connected authors' embeddings.

    Outputs a single Parquet file with:
    - `entity_type`
    - `embedding`
    - `projection_x` / `projection_y` (2D UMAP coordinates)
    """

    typer.echo(f"Loading graph from {input_graphml}...")
    graph = load_graphml_to_rx(str(input_graphml))
    typer.echo(f"Graph loaded: {graph.num_nodes()} nodes, {graph.num_edges()} edges")

    # Build a map of entity type -> list of node indices
    node_type_map: dict[str, list[int]] = {}
    for idx in graph.node_indices():
        attrs = graph.get_node_data(idx) or {}
        ntype = attrs.get("type", "unknown")
        node_type_map.setdefault(ntype, []).append(idx)

    type_summary = {k: len(v) for k, v in node_type_map.items()}
    typer.echo(f"Node types: {type_summary}")

    all_entities: list[dict] = []

    # --- Step 1: Embed works ---
    typer.echo("\nStep 1/4: Embedding works...")
    work_embeddings = _embed_works(graph, node_type_map, model_name=model, batch_size=batch_size)
    all_entities.extend(_collect_entities(graph, node_type_map.get("source", []), work_embeddings, "work"))

    # --- Step 2: Embed authors ---
    typer.echo("\nStep 2/4: Embedding authors...")
    author_embeddings = _embed_authors(
        graph,
        node_type_map,
        work_embeddings,
    )
    all_entities.extend(_collect_entities(graph, node_type_map.get("author", []), author_embeddings, "author"))

    # --- Step 3: Embed topics ---
    typer.echo("\nStep 3/4: Embedding topics...")
    topic_embeddings = _embed_topics(graph, node_type_map, work_embeddings)
    all_entities.extend(_collect_entities(graph, node_type_map.get("topic", []), topic_embeddings, "topic"))

    # --- Step 4: Embed institutions ---
    typer.echo("\nStep 4/4: Embedding institutions...")
    inst_embeddings = _embed_institutions(graph, node_type_map, author_embeddings)
    all_entities.extend(_collect_entities(graph, node_type_map.get("institution", []), inst_embeddings, "institution"))

    # --- Step 5: Compute 2D UMAP projection ---
    typer.echo("\nStep 5/5: Computing UMAP 2D projection...")
    _compute_umap_coordinates(
        all_entities,
        n_neighbors=umap_n_neighbors,
        min_dist=umap_min_dist,
        metric=umap_metric,
        random_state=umap_random_state,
    )

    # --- Write output ---
    typer.echo(f"\nWriting {len(all_entities)} entities to {output_file}...")
    _save_to_parquet(all_entities, output_file)

    typer.echo("Done.")


app.command(name="trajectory")(trajectory_command)


if __name__ == "__main__":
    app()

