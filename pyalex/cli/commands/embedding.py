"""Embedding command for PyAlex CLI."""

import json
from pathlib import Path
from typing import Annotated
from typing import Any

import typer

from sentence_transformers import SentenceTransformer

# SentenceTransformer: Any | None = None
# try:  # pragma: no cover - optional dependency
#     import sentence_transformers  # type: ignore[import-not-found]
# except ImportError:
#     pass
# else:
#     SentenceTransformer = sentence_transformers.SentenceTransformer


def embed(
    file_path: Annotated[
        str,
        typer.Argument(
            help="Path to the JSONL or Parquet file containing records to embed",
        ),
    ],
    text_field: Annotated[
        str,
        typer.Option(
            "--text",
            help="Field name containing the text to embed",
        ),
    ],
    model_name: Annotated[
        str,
        typer.Option(
            "--model",
            help="Sentence-Transformers model to use",
        ),
    ] = "sentence-transformers/all-MiniLM-L6-v2",
    embedding_field: Annotated[
        str,
        typer.Option(
            "--embedding",
            help="Field name to store the generated embedding",
        ),
    ] = "embedding",
    output_path: Annotated[
        str | None,
        typer.Option(
            "--output",
            help=(
                "Path for the output file (defaults to overwriting the input file)"
            ),
        ),
    ] = None,
):
    """Generate embeddings for a text field and persist them alongside the data."""

    input_path = Path(file_path)
    if not input_path.exists():
        typer.echo(f"Error: File '{input_path}' not found", err=True)
        raise typer.Exit(1)

    ext = input_path.suffix.lower()
    if ext not in {".jsonl", ".ndjson", ".parquet"}:
        typer.echo("Error: Only .jsonl and .parquet files are supported", err=True)
        raise typer.Exit(1)

    if SentenceTransformer is None:
        typer.echo(
            "Error: sentence-transformers package is required for 'pyalex embed'.",
            err=True,
        )
        raise typer.Exit(1)

    assert SentenceTransformer is not None
    try:
        model = SentenceTransformer(model_name)
    except Exception as exc:  # pragma: no cover - model loading issue
        typer.echo(
            f"Error: Failed to load model '{model_name}': {exc}",
            err=True,
        )
        raise typer.Exit(1) from exc

    records: list[dict[str, Any]]
    if ext in {".jsonl", ".ndjson"}:
        records = _read_jsonl_records(input_path)
    else:
        records = _read_parquet_records(input_path)

    if not records:
        typer.echo("Warning: No records found; nothing to embed.")
        return

    missing = [idx for idx, record in enumerate(records) if text_field not in record]
    if missing:
        typer.echo(
            f"Error: Field '{text_field}' is missing in {len(missing)} record(s)",
            err=True,
        )
        raise typer.Exit(1)

    texts = [str(record[text_field]) for record in records]
    try:
        embeddings = model.encode(texts, batch_size=32, show_progress_bar=False)
    except TypeError:
        embeddings = model.encode(texts)

    processed_embeddings: list[list[float]] = []
    for embedding in embeddings:
        if hasattr(embedding, "tolist"):
            processed_embeddings.append(list(embedding.tolist()))
        elif isinstance(embedding, (list, tuple)):
            processed_embeddings.append([float(val) for val in embedding])
        else:
            typer.echo(
                "Error: Unexpected embedding format returned by the model",
                err=True,
            )
            raise typer.Exit(1)

    for record, embedding_vector in zip(records, processed_embeddings, strict=True):
        record[embedding_field] = embedding_vector

    destination = Path(output_path) if output_path else input_path
    if ext in {".jsonl", ".ndjson"}:
        _write_jsonl_records(destination, records)
    else:
        _write_parquet_records(destination, records)

    typer.echo(f"Embeddings saved to {destination}")


def _read_jsonl_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise typer.BadParameter(
                    f"Invalid JSON on line {line_number} of {path}: {exc}"
                ) from exc
            if not isinstance(parsed, dict):
                raise typer.BadParameter(
                    f"Expected an object on line {line_number} of {path}"
                )
            records.append(parsed)
    return records


def _write_jsonl_records(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _read_parquet_records(path: Path) -> list[dict[str, Any]]:
    import pandas as pd  # type: ignore[import-not-found]

    try:
        df = pd.read_parquet(path)
    except Exception as exc:
        raise typer.BadParameter(
            f"Failed to read parquet file '{path}': {exc}"
        ) from exc
    return df.to_dict(orient="records")


def _write_parquet_records(path: Path, records: list[dict[str, Any]]) -> None:
    import pandas as pd  # type: ignore[import-not-found]

    df = pd.DataFrame(records)
    df.to_parquet(path, index=False)


def create_embedding_command(app: typer.Typer) -> None:
    """Register the embedding command."""
    app.command()(embed)
