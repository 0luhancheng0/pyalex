"""Collaboration prediction experiment — CLI entry point.

Evaluates which embedding aggregation strategy best predicts future
co-authorship. Uses a temporal split: author embeddings are computed
from pre-cutoff works, then evaluated against post-cutoff labels.

Usage
-----
    python collaboration_prediction.py prepare network.graphml \\
        --cutoff-year 2016 --min-works 3 -o results.json

    python collaboration_prediction.py evaluate results.json
"""

import json
import sys
from pathlib import Path

# Ensure sibling modules (aggregations, graph_utils, metrics) are importable
# regardless of the working directory the script is invoked from.
sys.path.insert(0, str(Path(__file__).parent))

from typing import Annotated

import numpy as np
import typer

from aggregations import STRATEGY_NAMES, compute_all_strategies
from graph_utils import (
    build_indices,
    get_post_cutoff_coauthor_pairs,
    get_pre_cutoff_works_for_author,
    get_text,
)
from metrics import evaluate_strategy, sample_negative_pairs
from pyalex.embeddings.data_loader import load_graphml_to_rx
from pyalex.embeddings.embed import generate_embeddings

app = typer.Typer(
    name="collaboration-prediction",
    help="Evaluate embedding aggregation strategies for collaboration prediction.",
    no_args_is_help=True,
)


@app.command()
def prepare(
    input_graphml: Annotated[
        Path,
        typer.Argument(help="GraphML file from `pyalex network build`.", exists=True),
    ],
    output_file: Annotated[
        Path,
        typer.Option("--output", "-o", help="Path to save results JSON."),
    ] = Path("results.json"),
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
        typer.Option("--batch-size", "-b", help="Embedding batch size."),
    ] = 32,
    seed: Annotated[
        int,
        typer.Option("--seed", help="Random seed for negative sampling."),
    ] = 42,
):
    """Prepare and evaluate all aggregation strategies in one pass."""
    typer.echo(f"Loading graph from {input_graphml}...")
    graph = load_graphml_to_rx(str(input_graphml))
    typer.echo(f"Graph: {graph.num_nodes()} nodes, {graph.num_edges()} edges")

    type_map, idx_to_id = build_indices(graph)
    typer.echo(f"Node types: { {k: len(v) for k, v in type_map.items()} }")

    # Step 1: Author -> pre-cutoff works mapping
    typer.echo(f"\nStep 1: Building author-work mapping (cutoff={cutoff_year})...")
    author_work_map: dict[str, list[int]] = {}
    for author_idx in type_map.get("author", []):
        aid = idx_to_id[author_idx]
        works = get_pre_cutoff_works_for_author(graph, author_idx, cutoff_year)
        if len(works) >= min_works:
            author_work_map[aid] = works
    typer.echo(f"  {len(author_work_map)} authors with >= {min_works} pre-cutoff works")

    if not author_work_map:
        typer.echo("Error: No eligible authors found.", err=True)
        raise typer.Exit(1)

    # Step 2: Work-level embeddings
    typer.echo("\nStep 2: Generating work-level embeddings...")
    all_work_indices = sorted(set(wi for wis in author_work_map.values() for wi in wis))
    texts = [get_text(graph.get_node_data(wi) or {}) for wi in all_work_indices]
    typer.echo(f"  Embedding {len(texts)} unique pre-cutoff works...")
    raw_embs = generate_embeddings(texts, model_name=model, batch_size=batch_size)

    work_embeddings: dict[int, np.ndarray] = {
        wi: np.array(emb, dtype=np.float32)
        for wi, emb in zip(all_work_indices, raw_embs)
        if emb is not None
    }
    typer.echo(f"  {len(work_embeddings)}/{len(all_work_indices)} works embedded")

    # Step 3: Author embeddings per strategy
    typer.echo("\nStep 3: Computing author embeddings (5 strategies)...")
    strategy_embeddings = compute_all_strategies(
        graph, author_work_map, work_embeddings, cutoff_year, model,
    )
    for name, embs in strategy_embeddings.items():
        typer.echo(f"  {name}: {len(embs)} authors")

    # Step 4: Evaluation pairs
    typer.echo("\nStep 4: Building evaluation pairs...")
    eligible = set(author_work_map.keys())
    positive_pairs = get_post_cutoff_coauthor_pairs(
        graph, type_map, idx_to_id, cutoff_year, eligible,
    )
    typer.echo(f"  Positive pairs: {len(positive_pairs)}")

    negative_pairs = sample_negative_pairs(list(eligible), positive_pairs, ratio=neg_ratio, seed=seed)
    typer.echo(f"  Negative pairs: {len(negative_pairs)}")

    # Step 5: Metrics
    typer.echo("\nStep 5: Evaluating strategies...")
    results: dict[str, dict] = {}
    for name in STRATEGY_NAMES:
        metrics = evaluate_strategy(strategy_embeddings[name], positive_pairs, negative_pairs)
        results[name] = metrics
        typer.echo(
            f"  {name:>25s} | AUC={metrics['auc_roc']:.4f}  "
            f"AP={metrics['avg_precision']:.4f}  "
            f"P@K={metrics['precision_at_k']:.4f}  "
            f"ρ={metrics['spearman_rho']:.4f}"
        )

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
        typer.Argument(help="JSON results file from `prepare`.", exists=True),
    ],
):
    """Display a formatted comparison table from saved results."""
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

    for name, metrics in sorted(results.items(), key=lambda x: x[1].get("auc_roc", 0), reverse=True):
        typer.echo(
            f"  {name:>25s} | {metrics['auc_roc']:>8.4f} | {metrics['avg_precision']:>8.4f} | "
            f"{metrics['precision_at_k']:>8.4f} | {metrics['spearman_rho']:>8.4f}"
        )
    typer.echo("=" * 72)


if __name__ == "__main__":
    app()
