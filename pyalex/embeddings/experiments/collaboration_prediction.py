"""Collaboration prediction experiment.

Evaluates which embedding aggregation strategy best predicts future
co-authorship between authors. Uses a temporal split: author embeddings
are computed from pre-cutoff works, then evaluated against post-cutoff
collaboration labels.

Usage
-----
    python -m pyalex.embeddings.experiments.collaboration_prediction prepare \\
        network.graphml --cutoff-year 2016 --min-works 3 -o experiment.parquet

    python -m pyalex.embeddings.experiments.collaboration_prediction evaluate \\
        experiment.parquet -o results.json
"""

import itertools
import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Annotated

import numpy as np
import pandas as pd
import rustworkx as rx
import typer

from pyalex.embeddings.data_loader import load_graphml_to_rx
from pyalex.embeddings.embed import generate_embeddings

logger = logging.getLogger(__name__)

app = typer.Typer(
    name="collaboration-prediction",
    help="Evaluate embedding aggregation strategies for collaboration prediction.",
    no_args_is_help=True,
)

# ---------------------------------------------------------------------------
# Aggregation strategies
# ---------------------------------------------------------------------------

STRATEGY_NAMES = [
    "mean",
    "recency_weighted",
    "citation_weighted",
    "concat_abstracts",
    "max_pool",
]


def _aggregate_mean(embeddings: list[np.ndarray], **_kwargs) -> np.ndarray:
    """Simple mean of work embeddings."""
    return np.mean(embeddings, axis=0).astype(np.float32)


def _aggregate_recency_weighted(
    embeddings: list[np.ndarray],
    years: list[int],
    cutoff_year: int,
    **_kwargs,
) -> np.ndarray:
    """Weight each work embedding by 1 / (cutoff_year - pub_year + 1)."""
    weights = np.array(
        [1.0 / (cutoff_year - y + 1) if y <= cutoff_year else 1.0 for y in years],
        dtype=np.float32,
    )
    weights /= weights.sum()
    stacked = np.stack(embeddings)
    return (weights[:, None] * stacked).sum(axis=0).astype(np.float32)


def _aggregate_citation_weighted(
    embeddings: list[np.ndarray],
    citations: list[int],
    **_kwargs,
) -> np.ndarray:
    """Weight each work embedding by log1p(cited_by_count)."""
    weights = np.array([np.log1p(c) for c in citations], dtype=np.float32)
    total = weights.sum()
    if total == 0:
        return np.mean(embeddings, axis=0).astype(np.float32)
    weights /= total
    stacked = np.stack(embeddings)
    return (weights[:, None] * stacked).sum(axis=0).astype(np.float32)


def _aggregate_max_pool(embeddings: list[np.ndarray], **_kwargs) -> np.ndarray:
    """Element-wise max across work embeddings."""
    return np.max(np.stack(embeddings), axis=0).astype(np.float32)


def _aggregate_concat_abstracts(
    texts: list[str],
    model_name: str = "all-MiniLM-L6-v2",
    **_kwargs,
) -> np.ndarray | None:
    """Concatenate titles+abstracts into one text string and embed."""
    composite = " | ".join(t for t in texts if t and t.strip())
    if not composite.strip():
        return None
    result = generate_embeddings([composite], model_name=model_name)
    if result and result[0] is not None:
        return np.array(result[0], dtype=np.float32)
    return None


# ---------------------------------------------------------------------------
# Graph helpers
# ---------------------------------------------------------------------------


def _parse_year(attrs: dict) -> int:
    """Extract publication year from node attributes, defaulting to 0."""
    raw = attrs.get("year", attrs.get("publication_year", 0))
    if isinstance(raw, str):
        raw = raw.split(".")[0]  # handle "2016.0" from GraphML
    return int(float(raw or 0))


def _parse_citations(attrs: dict) -> int:
    raw = attrs.get("cited_by_count", 0)
    if isinstance(raw, str):
        raw = raw.split(".")[0]
    return int(float(raw or 0))


def _get_text(attrs: dict) -> str:
    """Build a text string from title + abstract."""
    title = attrs.get("title", "") or ""
    abstract = attrs.get("abstract", "") or ""
    return f"{title} {abstract}".strip()


def _build_indices(
    graph: rx.PyDiGraph,
) -> tuple[
    dict[str, list[int]],   # node_type -> [node_idx]
    dict[int, str],          # node_idx -> entity_id
]:
    """Index all nodes by type and build an idx-to-id map."""
    type_map: dict[str, list[int]] = defaultdict(list)
    idx_to_id: dict[int, str] = {}
    for idx in graph.node_indices():
        attrs = graph.get_node_data(idx) or {}
        ntype = attrs.get("type", "unknown")
        eid = attrs.get("id", f"node_{idx}")
        type_map[ntype].append(idx)
        idx_to_id[idx] = eid
    return dict(type_map), idx_to_id


# ---------------------------------------------------------------------------
# Temporal splitting
# ---------------------------------------------------------------------------


def _get_pre_cutoff_works_for_author(
    graph: rx.PyDiGraph,
    author_idx: int,
    cutoff_year: int,
) -> list[int]:
    """Return indices of work nodes connected to an author with year <= cutoff."""
    work_indices = []
    for pred_idx in graph.predecessor_indices(author_idx):
        attrs = graph.get_node_data(pred_idx) or {}
        if attrs.get("type") != "source":
            continue
        if _parse_year(attrs) <= cutoff_year:
            work_indices.append(pred_idx)
    return work_indices


def _get_post_cutoff_coauthor_pairs(
    graph: rx.PyDiGraph,
    type_map: dict[str, list[int]],
    idx_to_id: dict[int, str],
    cutoff_year: int,
    eligible_authors: set[str],
) -> set[tuple[str, str]]:
    """Find author pairs who co-authored a work published after cutoff_year.

    Only considers authors in *eligible_authors*.
    Returns a set of sorted tuples (id_A, id_B) with id_A < id_B.
    """
    pairs: set[tuple[str, str]] = set()
    for work_idx in type_map.get("source", []):
        attrs = graph.get_node_data(work_idx) or {}
        if _parse_year(attrs) <= cutoff_year:
            continue
        # Find all author successors of this work
        author_ids = []
        for succ_idx in graph.successor_indices(work_idx):
            succ_attrs = graph.get_node_data(succ_idx) or {}
            if succ_attrs.get("type") == "author":
                aid = idx_to_id.get(succ_idx)
                if aid and aid in eligible_authors:
                    author_ids.append(aid)
        for a, b in itertools.combinations(sorted(author_ids), 2):
            pairs.add((a, b))
    return pairs


# ---------------------------------------------------------------------------
# Embedding computation per strategy
# ---------------------------------------------------------------------------


def _compute_all_strategies(
    graph: rx.PyDiGraph,
    author_work_map: dict[str, list[int]],
    work_embeddings: dict[int, np.ndarray],
    cutoff_year: int,
    model_name: str,
) -> dict[str, dict[str, np.ndarray]]:
    """Compute author embeddings under every aggregation strategy.

    Returns ``{strategy_name: {author_id: embedding}}``.
    """
    results: dict[str, dict[str, np.ndarray]] = {s: {} for s in STRATEGY_NAMES}

    for author_id, work_indices in author_work_map.items():
        embs = [work_embeddings[wi] for wi in work_indices if wi in work_embeddings]
        if not embs:
            continue

        attrs_list = [graph.get_node_data(wi) or {} for wi in work_indices]
        years = [_parse_year(a) for a in attrs_list]
        citations = [_parse_citations(a) for a in attrs_list]
        texts = [_get_text(a) for a in attrs_list]

        results["mean"][author_id] = _aggregate_mean(embs)
        results["recency_weighted"][author_id] = _aggregate_recency_weighted(
            embs, years=years, cutoff_year=cutoff_year,
        )
        results["citation_weighted"][author_id] = _aggregate_citation_weighted(
            embs, citations=citations,
        )
        results["max_pool"][author_id] = _aggregate_max_pool(embs)

        concat_result = _aggregate_concat_abstracts(texts, model_name=model_name)
        if concat_result is not None:
            results["concat_abstracts"][author_id] = concat_result

    return results


# ---------------------------------------------------------------------------
# Evaluation helpers
# ---------------------------------------------------------------------------


def _sample_negative_pairs(
    eligible_authors: list[str],
    positive_pairs: set[tuple[str, str]],
    ratio: int = 10,
    seed: int = 42,
) -> list[tuple[str, str]]:
    """Sample negative (non-collaborating) pairs."""
    rng = np.random.default_rng(seed)
    n_target = len(positive_pairs) * ratio
    all_authors = sorted(eligible_authors)
    negatives: list[tuple[str, str]] = []
    attempts = 0
    max_attempts = n_target * 20

    while len(negatives) < n_target and attempts < max_attempts:
        i, j = rng.choice(len(all_authors), size=2, replace=False)
        a, b = all_authors[min(i, j)], all_authors[max(i, j)]
        if (a, b) not in positive_pairs:
            negatives.append((a, b))
        attempts += 1

    return negatives


def _evaluate_strategy(
    embeddings: dict[str, np.ndarray],
    positive_pairs: set[tuple[str, str]],
    negative_pairs: list[tuple[str, str]],
) -> dict[str, float]:
    """Compute evaluation metrics for one strategy."""
    from sklearn.metrics import average_precision_score, roc_auc_score
    from sklearn.metrics.pairwise import cosine_similarity as cos_sim
    from scipy.stats import spearmanr

    all_pairs = [(a, b, 1) for a, b in positive_pairs] + [
        (a, b, 0) for a, b in negative_pairs
    ]

    similarities = []
    labels = []
    skipped = 0

    for a, b, label in all_pairs:
        if a not in embeddings or b not in embeddings:
            skipped += 1
            continue
        sim = cos_sim(
            embeddings[a].reshape(1, -1),
            embeddings[b].reshape(1, -1),
        )[0, 0]
        similarities.append(float(sim))
        labels.append(label)

    if not labels or sum(labels) == 0 or sum(labels) == len(labels):
        return {"auc_roc": 0.0, "avg_precision": 0.0, "spearman_rho": 0.0, "n_pairs": 0, "skipped": skipped}

    sims = np.array(similarities)
    labs = np.array(labels)

    auc = float(roc_auc_score(labs, sims))
    ap = float(average_precision_score(labs, sims))
    rho, _ = spearmanr(sims, labs)

    # Precision@K  (K = number of positives)
    k = int(labs.sum())
    top_k_indices = np.argsort(sims)[::-1][:k]
    precision_at_k = float(labs[top_k_indices].mean())

    return {
        "auc_roc": round(auc, 4),
        "avg_precision": round(ap, 4),
        "precision_at_k": round(precision_at_k, 4),
        "spearman_rho": round(float(rho), 4),
        "n_positive": int(labs.sum()),
        "n_negative": int((1 - labs).sum()),
        "n_pairs": len(labs),
        "skipped": skipped,
    }


# ---------------------------------------------------------------------------
# CLI commands
# ---------------------------------------------------------------------------


@app.command()
def prepare(
    input_graphml: Annotated[
        Path,
        typer.Argument(help="GraphML file from `pyalex network build`.", exists=True),
    ],
    output_file: Annotated[
        Path,
        typer.Option("--output", "-o", help="Path to save prepared experiment data."),
    ] = Path("experiment_data.json"),
    cutoff_year: Annotated[
        int,
        typer.Option("--cutoff-year", "-y", help="Temporal split year."),
    ] = 2016,
    min_works: Annotated[
        int,
        typer.Option("--min-works", "-n", help="Minimum pre-cutoff works per author."),
    ] = 3,
    neg_ratio: Annotated[
        int,
        typer.Option("--neg-ratio", help="Negative-to-positive sampling ratio."),
    ] = 10,
    model: Annotated[
        str,
        typer.Option("--model", "-m", help="SentenceTransformer model name."),
    ] = "all-MiniLM-L6-v2",
    batch_size: Annotated[
        int,
        typer.Option("--batch-size", "-b", help="Batch size for embedding generation."),
    ] = 32,
    seed: Annotated[
        int,
        typer.Option("--seed", help="Random seed for negative sampling."),
    ] = 42,
):
    """Prepare experiment data: split graph, compute embeddings, sample pairs."""
    typer.echo(f"Loading graph from {input_graphml}...")
    graph = load_graphml_to_rx(str(input_graphml))
    typer.echo(f"Graph: {graph.num_nodes()} nodes, {graph.num_edges()} edges")

    type_map, idx_to_id = _build_indices(graph)
    typer.echo(f"Node types: { {k: len(v) for k, v in type_map.items()} }")

    # --- Step 1: Build author -> pre-cutoff works mapping ---
    typer.echo(f"\nStep 1: Building author-work mapping (cutoff={cutoff_year})...")
    author_work_map: dict[str, list[int]] = {}
    for author_idx in type_map.get("author", []):
        aid = idx_to_id[author_idx]
        works = _get_pre_cutoff_works_for_author(graph, author_idx, cutoff_year)
        if len(works) >= min_works:
            author_work_map[aid] = works

    typer.echo(f"  {len(author_work_map)} authors with >= {min_works} pre-cutoff works")

    if not author_work_map:
        typer.echo("Error: No eligible authors found.", err=True)
        raise typer.Exit(1)

    # --- Step 2: Generate work-level embeddings ---
    typer.echo("\nStep 2: Generating work-level embeddings...")
    all_work_indices = sorted(
        set(wi for wis in author_work_map.values() for wi in wis)
    )
    texts = [_get_text(graph.get_node_data(wi) or {}) for wi in all_work_indices]
    typer.echo(f"  Embedding {len(texts)} unique pre-cutoff works...")
    raw_embs = generate_embeddings(texts, model_name=model, batch_size=batch_size)

    work_embeddings: dict[int, np.ndarray] = {}
    for wi, emb in zip(all_work_indices, raw_embs):
        if emb is not None:
            work_embeddings[wi] = np.array(emb, dtype=np.float32)

    typer.echo(f"  {len(work_embeddings)}/{len(all_work_indices)} works embedded successfully")

    # --- Step 3: Compute author embeddings via all strategies ---
    typer.echo("\nStep 3: Computing author embeddings (5 strategies)...")
    strategy_embeddings = _compute_all_strategies(
        graph, author_work_map, work_embeddings, cutoff_year, model,
    )
    for name, embs in strategy_embeddings.items():
        typer.echo(f"  {name}: {len(embs)} authors")

    # --- Step 4: Build evaluation pairs ---
    typer.echo("\nStep 4: Building evaluation pairs...")
    eligible = set(author_work_map.keys())
    positive_pairs = _get_post_cutoff_coauthor_pairs(
        graph, type_map, idx_to_id, cutoff_year, eligible,
    )
    typer.echo(f"  Positive pairs (post-cutoff collaborations): {len(positive_pairs)}")

    negative_pairs = _sample_negative_pairs(
        list(eligible), positive_pairs, ratio=neg_ratio, seed=seed,
    )
    typer.echo(f"  Negative pairs (sampled): {len(negative_pairs)}")

    # --- Step 5: Evaluate ---
    typer.echo("\nStep 5: Evaluating strategies...")
    results: dict[str, dict] = {}
    for strategy_name in STRATEGY_NAMES:
        embs = strategy_embeddings[strategy_name]
        metrics = _evaluate_strategy(embs, positive_pairs, negative_pairs)
        results[strategy_name] = metrics
        typer.echo(
            f"  {strategy_name:>25s} | AUC={metrics['auc_roc']:.4f}  "
            f"AP={metrics['avg_precision']:.4f}  "
            f"P@K={metrics['precision_at_k']:.4f}  "
            f"ρ={metrics['spearman_rho']:.4f}"
        )

    # --- Save results ---
    output = {
        "config": {
            "cutoff_year": cutoff_year,
            "min_works": min_works,
            "neg_ratio": neg_ratio,
            "model": model,
            "seed": seed,
            "n_eligible_authors": len(author_work_map),
            "n_pre_cutoff_works": len(work_embeddings),
            "n_positive_pairs": len(positive_pairs),
            "n_negative_pairs": len(negative_pairs),
        },
        "results": results,
    }

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)
    typer.echo(f"\nResults saved to {output_file}")


@app.command()
def evaluate(
    results_file: Annotated[
        Path,
        typer.Argument(help="JSON results file from `prepare` command.", exists=True),
    ],
):
    """Display a formatted summary of experiment results."""
    with open(results_file) as f:
        data = json.load(f)

    config = data["config"]
    results = data["results"]

    typer.echo("=" * 72)
    typer.echo("  Collaboration Prediction — Embedding Aggregation Comparison")
    typer.echo("=" * 72)
    typer.echo(f"  Cutoff year          : {config['cutoff_year']}")
    typer.echo(f"  Min pre-cutoff works : {config['min_works']}")
    typer.echo(f"  Embedding model      : {config['model']}")
    typer.echo(f"  Eligible authors     : {config['n_eligible_authors']}")
    typer.echo(f"  Pre-cutoff works     : {config['n_pre_cutoff_works']}")
    typer.echo(f"  Positive pairs       : {config['n_positive_pairs']}")
    typer.echo(f"  Negative pairs       : {config['n_negative_pairs']}")
    typer.echo("-" * 72)
    typer.echo(f"  {'Strategy':>25s} | {'AUC-ROC':>8s} | {'Avg Prec':>8s} | {'P@K':>8s} | {'Spearman':>8s}")
    typer.echo("-" * 72)

    # Sort by AUC descending
    for name, metrics in sorted(results.items(), key=lambda x: x[1].get("auc_roc", 0), reverse=True):
        typer.echo(
            f"  {name:>25s} | {metrics['auc_roc']:>8.4f} | {metrics['avg_precision']:>8.4f} | "
            f"{metrics['precision_at_k']:>8.4f} | {metrics['spearman_rho']:>8.4f}"
        )
    typer.echo("=" * 72)


if __name__ == "__main__":
    app()
