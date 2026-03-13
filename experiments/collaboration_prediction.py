"""Collaboration prediction experiment — CLI entry point.

Samples temporal link-prediction supervision pairs from a collaboration graph.
The `sample` command writes positive/negative author-pair CSVs.
The `evaluate` command consumes the original GraphML plus those CSVs.

Usage
-----
    python collaboration_prediction.py sample network.graphml \\
        --cutoff-year 2016 \\
        --positive-output positive_pairs.csv \\
        --negative-output negative_pairs.csv

    python collaboration_prediction.py evaluate network.graphml \\
        --embeddings-file embeddings.parquet \\
        --positive-pairs positive_pairs.csv \\
        --negative-pairs negative_pairs.csv \\
        -o results.json
"""

import json
import sys
from pathlib import Path

# Ensure sibling modules are importable regardless of the working directory.
sys.path.insert(0, str(Path(__file__).parent))

from typing import Annotated, Optional

import typer

import pipeline

app = typer.Typer(
    name="collaboration-prediction",
    help="Prepare and evaluate collaboration prediction datasets.",
    no_args_is_help=True,
)


@app.command()
def sample(
    input_graphml: Annotated[
        Path,
        typer.Argument(help="GraphML file from `pyalex network build`.", exists=True),
    ],
    positive_output: Annotated[
        Path,
        typer.Option("--positive-output", help="CSV file for positive (post-cutoff) pairs."),
    ] = Path("positive_pairs.csv"),
    negative_output: Annotated[
        Path,
        typer.Option("--negative-output", help="CSV file for sampled negative pairs."),
    ] = Path("negative_pairs.csv"),
    cutoff_year: Annotated[
        int,
        typer.Option("--cutoff-year", "-y", help="Temporal split year."),
    ] = 2016,
    neg_ratio: Annotated[
        int,
        typer.Option("--neg-ratio", help="Negative-to-positive sampling ratio."),
    ] = 10,
    neg_strategy: Annotated[
        str,
        typer.Option("--neg-strategy", help="Negative sampling strategy: 'random' or 'hard_graph'."),
    ] = "random",
    seed: Annotated[
        int,
        typer.Option("--seed", help="Random seed for negative sampling."),
    ] = 42,
):
    """Sample positive and negative author pairs for link-prediction evaluation."""
    typer.echo(f"Loading graph from {input_graphml}...")
    graph, type_map, idx_to_id = pipeline.load_graph(str(input_graphml))
    typer.echo(f"  {graph.num_nodes()} nodes, {graph.num_edges()} edges")
    typer.echo(f"  Node types: { {k: len(v) for k, v in type_map.items()} }")

    eligible = set(idx_to_id[idx] for idx in type_map.get("author", []))
    if not eligible:
        typer.echo("Error: No author nodes found in graph.", err=True)
        raise typer.Exit(1)
    typer.echo(f"\n{len(eligible)} eligible authors found")

    typer.echo("Sampling pairs...")
    try:
        positive_pairs, negative_pairs = pipeline.sample_pairs(
            graph, type_map, idx_to_id, eligible,
            cutoff_year, neg_ratio, neg_strategy, seed,
        )
    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"  Positive: {len(positive_pairs)}, Negative: {len(negative_pairs)}")

    positive_output.parent.mkdir(parents=True, exist_ok=True)
    negative_output.parent.mkdir(parents=True, exist_ok=True)
    pipeline.write_pairs_csv(
        positive_pairs, negative_pairs,
        str(positive_output), str(negative_output),
        cutoff_year, neg_strategy, seed,
    )
    typer.echo(f"  Positive pairs → {positive_output}")
    typer.echo(f"  Negative pairs → {negative_output}")


@app.command()
def evaluate(
    input_graphml: Annotated[
        Path,
        typer.Argument(help="GraphML file from `pyalex network build`.", exists=True),
    ],
    positive_pairs_file: Annotated[
        Path,
        typer.Option("--positive-pairs", help="Positive-pairs CSV from `sample`.", exists=True),
    ] = Path("positive_pairs.csv"),
    negative_pairs_file: Annotated[
        Path,
        typer.Option("--negative-pairs", help="Negative-pairs CSV from `sample`.", exists=True),
    ] = Path("negative_pairs.csv"),
    embeddings_file: Annotated[
        Path,
        typer.Option("--embeddings-file", help="Parquet file from `pyalex embedding generate`.", exists=True),
    ] = Path("embeddings.parquet"),
    output_file: Annotated[
        Optional[Path],
        typer.Option("--output", "-o", help="Path to save final results JSON."),
    ] = None,
    predictions_output: Annotated[
        Optional[Path],
        typer.Option("--predictions-output", help="Path to save all pair predictions and scores as JSON."),
    ] = None,
    model_name: Annotated[
        str,
        typer.Option("--model", "-m", help="SentenceTransformer model for the concat_abstracts strategy."),
    ] = "all-MiniLM-L6-v2",
):
    """Run evaluation and display comparison table from a network graph and pair CSVs."""
    from aggregations import STRATEGY_NAMES, compute_all_strategies
    from metrics import evaluate_strategy

    typer.echo(f"Loading graph from {input_graphml}...")
    graph, type_map, idx_to_id = pipeline.load_graph(str(input_graphml))
    typer.echo(f"  {graph.num_nodes()} nodes, {graph.num_edges()} edges")

    positive_pairs, negative_pairs, cutoff_year, neg_strategy = pipeline.read_pairs_csv(
        str(positive_pairs_file), str(negative_pairs_file),
    )
    typer.echo(f"  Positive: {len(positive_pairs)}, Negative: {len(negative_pairs)}, Cutoff: {cutoff_year}")

    work_embeddings, work_texts_data = pipeline.extract_work_data(
        graph,
        embeddings_parquet=str(embeddings_file),
    )
    typer.echo(f"  Work nodes: {len(work_texts_data)}, with embeddings: {len(work_embeddings)}")

    author_work_map = pipeline.build_author_work_map(graph, type_map, idx_to_id, cutoff_year)
    typer.echo(f"  Authors with pre-cutoff works: {len(author_work_map)}")

    typer.echo("\nComputing strategy embeddings and evaluating...")
    strategy_embeddings = compute_all_strategies(
        author_work_map, work_embeddings, work_texts_data, cutoff_year, model_name,
    )

    results: dict[str, dict] = {}
    all_predictions: dict[str, list[dict]] = {}
    for name in STRATEGY_NAMES:
        embs = strategy_embeddings.get(name, {})
        if not embs:
            typer.echo(f"  Skipping '{name}' — no embeddings computed.")
            continue
        
        eval_result = evaluate_strategy(
            embs, positive_pairs, negative_pairs, return_predictions=bool(predictions_output)
        )
        if bool(predictions_output) and "predictions" in eval_result:
            all_predictions[name] = eval_result.pop("predictions")
            
        results[name] = eval_result

    typer.echo("=" * 72)
    typer.echo("  Collaboration Prediction — Embedding Aggregation Comparison")
    typer.echo("=" * 72)
    typer.echo(f"  Input file           : {input_graphml}")
    typer.echo(f"  Cutoff year          : {cutoff_year}")
    typer.echo(f"  Embedding model      : {model_name}")
    typer.echo(f"  Authors w/ works     : {len(author_work_map)}")
    typer.echo(f"  Negative strategy    : {neg_strategy}")
    typer.echo(f"  Positive pairs       : {len(positive_pairs)}")
    typer.echo(f"  Negative pairs       : {len(negative_pairs)}")
    typer.echo("-" * 72)
    typer.echo(f"  {'Strategy':>25s} | {'AUC-ROC':>8s} | {'Avg Prec':>8s} | {'P@K':>8s} | {'Hits@10':>8s} | {'Hits@100':>8s}")
    typer.echo("-" * 72)
    for name, m in sorted(results.items(), key=lambda x: x[1].get("auc_roc", 0), reverse=True):
        typer.echo(
            f"  {name:>25s} | {m['auc_roc']:>8.4f} | {m['avg_precision']:>8.4f} | "
            f"{m['precision_at_k']:>8.4f} | {m.get('hits_at_10', 0):>8.4f} | {m.get('hits_at_100', 0):>8.4f}"
        )
    typer.echo("=" * 72)

    if output_file:
        with open(output_file, "w") as f:
            json.dump({
                "config": {
                    "input_file": str(input_graphml),
                    "embeddings_file": str(embeddings_file),
                    "positive_pairs_file": str(positive_pairs_file),
                    "negative_pairs_file": str(negative_pairs_file),
                    "cutoff_year": cutoff_year,
                    "model": model_name,
                    "n_authors_with_works": len(author_work_map),
                    "neg_strategy": neg_strategy,
                    "n_positive_pairs": len(positive_pairs),
                    "n_negative_pairs": len(negative_pairs),
                },
                "results": results,
            }, f, indent=2)
        typer.echo(f"\nResults saved to {output_file}")

    if predictions_output:
        with open(predictions_output, "w") as f:
            json.dump(all_predictions, f, indent=2)
        typer.echo(f"\nPredictions saved to {predictions_output}")

if __name__ == "__main__":
    app()
