"""
Interactive embedding atlas visualization command for PyAlex CLI.

This command uses the 'embedding-atlas' package to provide a high-performance,
web-based visualization of entity embeddings.
"""

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Annotated, List, Optional

import typer
import pandas as pd

from ..utils import _handle_cli_exception


def _load_jsonl_to_df(input_files: List[Path]) -> pd.DataFrame:
    """
    Load entities from a list of JSONL files into a Pandas DataFrame.
    """
    all_data = []
    for file_path in input_files:
        typer.echo(f"Reading data from {file_path}...")
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    # Add source file metadata
                    data["_source_file"] = file_path.name
                    all_data.append(data)
                except json.JSONDecodeError:
                    continue
    
    if not all_data:
        return pd.DataFrame()
        
    df = pd.DataFrame(all_data)
    return df


atlas_app = typer.Typer(
    name="atlas",
    help="Interactive embedding visualization using Apple's Embedding Atlas",
    no_args_is_help=True,
)


@atlas_app.command(name="visualize")
def visualize(
    input_path: Annotated[
        Path,
        typer.Option(
            "--input-path",
            "-i",
            help="Path to the entities JSONL file or directory containing JSONL files",
            exists=True,
            file_okay=True,
            dir_okay=True,
            readable=True,
        ),
    ],
    port: Annotated[
        int,
        typer.Option(
            "--port",
            "-p",
            help="Port to run the visualization server on",
        ),
    ] = 5055,
):
    """
    Launch an interactive Embedding Atlas visualization from JSONL data.
    """
    try:
        # Check if embedding-atlas is available in the environment
        try:
            # We don't use subprocess.check_output because we just want to know if it's there
            subprocess.run(["embedding-atlas", "--version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            typer.echo(
                "Error: embedding-atlas CLI is not available.", err=True
            )
            typer.echo("Please install it with: pip install embedding-atlas", err=True)
            raise typer.Exit(1)

        # 1. Determine Input Files
        if input_path.is_dir():
            input_files = list(input_path.glob("*.jsonl"))
            if not input_files:
                typer.echo(f"No .jsonl files found in {input_path}", err=True)
                raise typer.Exit(1)
        else:
            input_files = [input_path]

        # 2. Load Data
        df = _load_jsonl_to_df(input_files)
        
        if df.empty:
            typer.echo("Error: No data found in input files.", err=True)
            raise typer.Exit(1)

        if "embedding" not in df.columns:
            typer.echo("Error: No 'embedding' column found in the data.", err=True)
            typer.echo("Ensure you generated embeddings when fetching the data (e.g., using --embeddings-model).", err=True)
            raise typer.Exit(1)

        # 3. Clean up complex columns for better visualization
        # Embedding Atlas likes flat metadata.
        for col in df.columns:
            if col != "embedding" and df[col].apply(lambda x: isinstance(x, (list, dict))).any():
                df[col] = df[col].apply(lambda x: json.dumps(x) if isinstance(x, (list, dict)) else x)

        typer.echo(f"Preparing Embedding Atlas for {len(df)} entities...")
        
        # Save to a temporary Parquet file for the atlas server
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
            tmp_path = tmp.name
            df.to_parquet(tmp_path, index=False)

        typer.echo(f"Launching Embedding Atlas on http://localhost:{port}...")
        try:
            # Run the server
            subprocess.run(["embedding-atlas", tmp_path, "--port", str(port), "--vector", "embedding"], check=True)
        finally:
            # Cleanup
            if Path(tmp_path).exists():
                Path(tmp_path).unlink()

    except Exception as e:
        _handle_cli_exception(e)


def create_atlas_command(app):
    """Create and register the atlas command suite."""
    app.add_typer(atlas_app)
