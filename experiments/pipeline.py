"""Orchestration pipeline for the collaboration prediction experiment.

Provides named, testable functions for each logical step so that the CLI
commands in *collaboration_prediction.py* remain thin wrappers.

All graph interaction is delegated to *graph_utils*, all sampling/metrics to
*metrics*, and all embedding strategies to *aggregations*.
"""

import csv

import numpy as np
import rustworkx as rx

from graph_utils import (
    build_indices,
    get_hard_negative_candidate_pairs,
    get_post_cutoff_coauthor_pairs,
    get_pre_cutoff_works_for_author,
)
from metrics import sample_hard_negative_pairs, sample_negative_pairs
from pyalex.embeddings.data_loader import load_graphml_to_rx


# ---------------------------------------------------------------------------
# Shared
# ---------------------------------------------------------------------------

def load_graph(
    path: str,
) -> tuple[rx.PyGraph | rx.PyDiGraph, dict[str, list[int]], dict[int, str]]:
    """Load a GraphML file and build node-type / id indices.

    Args:
        path: Path to the GraphML file.

    Returns:
        (graph, type_map, idx_to_id)
    """
    graph = load_graphml_to_rx(path)
    type_map, idx_to_id = build_indices(graph)
    return graph, type_map, idx_to_id


# ---------------------------------------------------------------------------
# Prepare pipeline steps
# ---------------------------------------------------------------------------

def sample_pairs(
    graph: rx.PyGraph | rx.PyDiGraph,
    type_map: dict[str, list[int]],
    idx_to_id: dict[int, str],
    eligible: set[str],
    cutoff_year: int,
    neg_ratio: int,
    neg_strategy: str,
    seed: int,
) -> tuple[set[tuple[str, str]], list[tuple[str, str]]]:
    """Identify positive pairs and sample negatives.

    Args:
        graph: The research network graph.
        type_map: Node type -> list of node indices.
        idx_to_id: Node index -> entity ID.
        eligible: Set of author IDs to consider.
        cutoff_year: Temporal split year.
        neg_ratio: Negatives per positive.
        neg_strategy: ``'random'`` or ``'hard_graph'``.
        seed: Random seed.

    Returns:
        (positive_pairs, negative_pairs)

    Raises:
        ValueError: If no collaboration edges are found.
    """
    positive_pairs = get_post_cutoff_coauthor_pairs(
        graph, type_map, idx_to_id, cutoff_year, eligible,
    )

    if neg_strategy == "hard_graph":
        candidates = get_hard_negative_candidate_pairs(
            graph, type_map, idx_to_id, cutoff_year, eligible,
        )
        n_target = len(positive_pairs) * neg_ratio
        negative_pairs = sample_hard_negative_pairs(
            candidates, positive_pairs, n_target=n_target, seed=seed,
        )
    else:
        negative_pairs = sample_negative_pairs(
            list(eligible), positive_pairs, ratio=neg_ratio, seed=seed,
        )

    return positive_pairs, negative_pairs


def write_pairs_csv(
    positive_pairs: set[tuple[str, str]],
    negative_pairs: list[tuple[str, str]],
    positive_path: str,
    negative_path: str,
    cutoff_year: int,
    neg_strategy: str,
    seed: int,
) -> None:
    """Write positive and negative pairs to separate CSV files.

    Each file starts with a metadata comment line so downstream consumers
    (e.g. ``evaluate``) can recover experiment settings without extra flags::

        # cutoff_year=2016,neg_strategy=random,seed=42
        author_a,author_b
        A123,A456
        ...

    Args:
        positive_pairs: Post-cutoff collaborating pairs.
        negative_pairs: Non-collaborating sampled pairs.
        positive_path: Output path for the positive-pairs CSV.
        negative_path: Output path for the negative-pairs CSV.
        cutoff_year: Stored in the metadata header.
        neg_strategy: Stored in the metadata header.
        seed: Stored in the metadata header.
    """
    meta = f"# cutoff_year={cutoff_year},neg_strategy={neg_strategy},seed={seed}\n"
    for path, pairs in ((positive_path, sorted(positive_pairs)), (negative_path, negative_pairs)):
        with open(path, "w", newline="") as f:
            f.write(meta)
            writer = csv.writer(f)
            writer.writerow(["author_a", "author_b"])
            writer.writerows(pairs)


def read_pairs_csv(
    positive_path: str,
    negative_path: str,
) -> tuple[set[tuple[str, str]], list[tuple[str, str]], int, str]:
    """Read positive and negative pairs from CSV files produced by ``write_pairs_csv``.

    Args:
        positive_path: Path to the positive-pairs CSV.
        negative_path: Path to the negative-pairs CSV.

    Returns:
        (positive_pairs, negative_pairs, cutoff_year, neg_strategy)
    """
    def _parse_meta(line: str) -> dict[str, str]:
        return dict(kv.split("=", 1) for kv in line.lstrip("# ").strip().split(",") if "=" in kv)

    def _load(path: str) -> tuple[list[tuple[str, str]], dict]:
        meta: dict = {}
        pairs: list[tuple[str, str]] = []
        with open(path, newline="") as f:
            for line in f:
                if line.startswith("#"):
                    meta = _parse_meta(line)
                    continue
                row = line.strip().split(",")
                if row[0] == "author_a" or len(row) < 2:
                    continue
                pairs.append((row[0], row[1]))
        return pairs, meta

    pos_pairs, meta = _load(positive_path)
    neg_pairs, _ = _load(negative_path)

    cutoff_year = int(meta.get("cutoff_year", 2016))
    neg_strategy = meta.get("neg_strategy", "random")
    return set(pos_pairs), neg_pairs, cutoff_year, neg_strategy


def extract_work_data(
    graph: rx.PyGraph | rx.PyDiGraph,
    embeddings_parquet: str | None = None,
) -> tuple[dict[str, np.ndarray], dict[str, dict]]:
    """Extract work embeddings and raw attribute dicts from the graph.

    Args:
        graph: The research network graph.
        embeddings_parquet: Optional parquet path from `pyalex embedding generate`.
            When provided, work embeddings are loaded from this file by matching
            `entity_type == "work"` and work `id`.

    Returns:
        (work_embeddings, work_texts_data) — keyed by work ID.
    """
    work_embeddings: dict[str, np.ndarray] = {}
    work_texts_data: dict[str, dict] = {}

    for node_idx in graph.node_indices():
        attrs = graph.get_node_data(node_idx) or {}
        if attrs.get("type") not in {"work", "source"}:
            continue
        work_id = attrs.get("id", f"node_{node_idx}")
        work_texts_data[work_id] = attrs
        if isinstance(attrs.get("embedding"), np.ndarray):
            work_embeddings[work_id] = attrs["embedding"]

    if embeddings_parquet:
        import json as _json
        import pandas as pd

        def _parse_embedding(value) -> np.ndarray | None:
            if isinstance(value, np.ndarray):
                return value.astype(np.float32)
            if isinstance(value, list):
                return np.array(value, dtype=np.float32)
            if isinstance(value, str):
                try:
                    parsed = _json.loads(value)
                    if isinstance(parsed, list):
                        return np.array(parsed, dtype=np.float32)
                except Exception:
                    return None
            return None

        df = pd.read_parquet(embeddings_parquet)
        if "entity_type" in df.columns:
            df = df[df["entity_type"] == "work"]

        id_col = "id" if "id" in df.columns else None
        emb_col = "embedding" if "embedding" in df.columns else None
        if id_col and emb_col:
            parquet_embeddings: dict[str, np.ndarray] = {}
            for work_id, emb_value in zip(df[id_col], df[emb_col]):
                emb = _parse_embedding(emb_value)
                if emb is not None:
                    parquet_embeddings[str(work_id)] = emb
            if parquet_embeddings:
                work_embeddings = parquet_embeddings

    return work_embeddings, work_texts_data


def build_author_work_map(
    graph: rx.PyGraph | rx.PyDiGraph,
    type_map: dict[str, list[int]],
    idx_to_id: dict[int, str],
    cutoff_year: int,
) -> dict[str, list[str]]:
    """Map each author to their pre-cutoff work IDs.

    Args:
        graph: The research network graph.
        type_map: Node type -> list of node indices.
        idx_to_id: Node index -> entity ID.
        cutoff_year: Only include works published on or before this year.

    Returns:
        ``{author_id: [work_id, ...]}`` for authors with at least one work.
    """
    author_work_map: dict[str, list[str]] = {}
    for author_idx in type_map.get("author", []):
        work_ids = get_pre_cutoff_works_for_author(graph, author_idx, cutoff_year)
        if work_ids:
            author_work_map[idx_to_id[author_idx]] = work_ids
    return author_work_map
