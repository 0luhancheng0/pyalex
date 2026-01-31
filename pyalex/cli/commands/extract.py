"""
Extract command for PyAlex CLI.

This command uses langextract to extract structured information from markdown files.
Currently supports dataset extraction with extensible design for future entity types.
"""

import json
import os
from pathlib import Path
from typing import Annotated, Optional, List

import typer
from langextract import extract
from langextract.data import ExampleData, Extraction, Document
import langextract as lx

from ..utils import _handle_cli_exception
from .help_panels import UTILITY_PANEL


# Entity type schemas for extraction
EXTRACTION_SCHEMAS = {
    "dataset": {
        "prompt_description": """Extract ONLY datasets that are directly used in the experiments or analysis described in the paper.

INCLUDE datasets that:
- Are explicitly used for training, testing, or evaluation
- Have results reported on them (accuracy, metrics, etc.)
- Are used as the primary data source for the study's methodology

EXCLUDE datasets that are:
- Only mentioned in related work or background sections without being used
- Referenced as examples or comparisons but not actually experimented on
- Cited from other papers without direct usage in this work
- Mentioned as "future work" or potential extensions

For each dataset used in experiments, extract: name, URL/DOI, description, version, size, and how it was used (training/testing/validation).""",
        "examples": [
            ExampleData(
                text="We trained our model on the ImageNet dataset (ILSVRC 2012) and evaluated on the CIFAR-10 test set, achieving 95.2% accuracy.",
                extractions=[
                    Extraction(
                        extraction_class="dataset",
                        extraction_text="ImageNet dataset (ILSVRC 2012)",
                        attributes={
                            "name": "ImageNet",
                            "version": "ILSVRC 2012",
                            "usage": "training"
                        }
                    ),
                    Extraction(
                        extraction_class="dataset",
                        extraction_text="CIFAR-10 test set",
                        attributes={
                            "name": "CIFAR-10",
                            "usage": "evaluation"
                        }
                    )
                ]
            ),
            ExampleData(
                text="While datasets like MNIST and Fashion-MNIST have been widely used in prior work, we focus our experiments on the OpenAlex dataset (https://openalex.org) containing 250M scholarly works for our citation network analysis.",
                extractions=[
                    Extraction(
                        extraction_class="dataset",
                        extraction_text="OpenAlex dataset (https://openalex.org) containing 250M scholarly works",
                        attributes={
                            "name": "OpenAlex",
                            "url": "https://openalex.org",
                            "description": "citation network analysis dataset",
                            "size": "250M scholarly works",
                            "usage": "primary analysis"
                        }
                    )
                    # Note: MNIST and Fashion-MNIST are NOT extracted because they are only mentioned as prior work
                ]
            )
        ]
    }
    # Future entity types can be added here:
    # "software": {...},
    # "method": {...},
    # "author": {...}
}


def extract_from_markdown_files(
    file_paths: List[Path],
    entity_type: str,
    model: str,
    api_key: Optional[str] = None,
    max_workers: int = None,
    extraction_pass: int = 1,
    enable_fuzzy_alignment: bool = True,
) -> tuple[List[dict], List]:
    """
    Extract entities from multiple markdown files using langextract with batch processing.
    
    This function batches all documents into a single langextract call,
    allowing concurrent LLM API calls for better performance.
    
    Args:
        file_paths: List of paths to markdown files
        entity_type: Type of entity to extract (e.g., "dataset")
        model: LLM model to use for extraction
        api_key: Optional OpenAI API key
        max_workers: Number of parallel workers for extraction
        extraction_pass: Number of extraction passes
        enable_fuzzy_alignment: Enable fuzzy matching for alignment
        
    Returns:
        Tuple of (results list with source_file added, list of AnnotatedDocument objects)
    """
    # Get schema for the entity type
    schema_config = EXTRACTION_SCHEMAS.get(entity_type)
    if not schema_config:
        raise ValueError(f"Unsupported entity type: {entity_type}. Supported types: {list(EXTRACTION_SCHEMAS.keys())}")
    
    # Read all markdown files and create Document objects
    documents = []
    for file_path in file_paths:
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        # Use file path as document_id for tracking
        doc = Document(text=text, document_id=str(file_path))
        documents.append(doc)
    
    typer.echo(f"Extracting {entity_type}s from {len(documents)} file(s) using {model}...")
    
    # Calculate max_char_buffer based on longest document
    max_text_len = max(len(doc.text) for doc in documents) if documents else 1000
    max_char_buffer = max_text_len + 1000  # Add safety margin
    
    # Call langextract with all documents in a batch for concurrent processing
    # The max_workers parameter enables parallel LLM API calls
    resolver_params = {"enable_fuzzy_alignment": enable_fuzzy_alignment}
    
    annotated_docs = extract(
        text_or_documents=documents,
        prompt_description=schema_config["prompt_description"],
        examples=schema_config["examples"],
        model_id=model,
        api_key=api_key if api_key else None,
        max_workers=max_workers if max_workers else os.cpu_count(),
        extraction_passes=extraction_pass,
        max_char_buffer=max_char_buffer,
        resolver_params=resolver_params,
    )
    
    # Process results - annotated_docs is an iterator when processing multiple documents
    all_results = []
    annotated_doc_list = []
    
    for annotated_doc in annotated_docs:
        annotated_doc_list.append(annotated_doc)
        # Extract source file from document_id
        source_file = annotated_doc.document_id
        
        for extraction in annotated_doc.extractions:
            result = extraction.attributes.copy() if extraction.attributes else {}
            result["extraction_text"] = extraction.extraction_text
            result["source_file"] = source_file
            all_results.append(result)
        
        # Log progress for each completed document
        extraction_count = len(annotated_doc.extractions)
        file_name = Path(source_file).name if source_file else "unknown"
        typer.echo(f"  ✓ Extracted {extraction_count} {entity_type}(s) from {file_name}")
    
    return all_results, annotated_doc_list


def create_extract_command(app: typer.Typer):
    """Create and register the extract command."""
    
    @app.command(name="extract", rich_help_panel=UTILITY_PANEL)
    def extract_entities(
        input_path: Annotated[
            Optional[str],
            typer.Argument(
                help="Path to input markdown file or directory containing markdown files. Required unless --visualize is used with a file.",
            ),
        ] = None,
        output: Annotated[
            Optional[str],
            typer.Option(
                "--output",
                "-o",
                help="Output JSONL file path (default: <input_file>.jsonl)",
            ),
        ] = None,
        entity_type: Annotated[
            str,
            typer.Option(
                "--type",
                "-t",
                help="Entity type to extract (currently supports: dataset)",
            ),
        ] = "dataset",
        model: Annotated[
            str,
            typer.Option(
                "--model",
                "-m",
                help="LLM model to use for extraction",
            ),
        ] = "gpt-5-mini",
        api_key: Annotated[
            Optional[str],
            typer.Option(
                "--api-key",
                help="OpenAI API key (uses OPENAI_API_KEY env var if not provided)",
                envvar="OPENAI_API_KEY",
            ),
        ] = None,
        visualize: Annotated[
            Optional[str],
            typer.Option(
                "--visualize",
                "-v",
                help="Generate interactive HTML visualization. Can be a boolean flag (visualize current extraction) or a file path (visualize existing JSONL).",
                flag_value="true",
            ),
        ] = None,
        max_workers: Annotated[
            Optional[int],
            typer.Option(
                "--max-workers",
                help="Number of parallel workers for extraction (default: number of CPU cores)",
            ),
        ] = None,
        extraction_pass: Annotated[
            int,
            typer.Option(
                "--extraction-pass",
                help="Number of extraction passes",
            ),
        ] = 1,
        enable_fuzzy_alignment: Annotated[
            bool,
            typer.Option(
                "--fuzzy-match/--no-fuzzy-match",
                help="Enable fuzzy matching for extraction alignment (default: True)",
            ),
        ] = True,
    ):
        """
        Extract structured information from markdown files using LLM-based extraction.
        
        This command uses langextract to identify and extract entities (e.g., datasets)
        mentioned in markdown documents. The extraction is performed using a language model
        with a defined schema for consistency.
        
        Examples:
        
            # Extract datasets from a single file
            pyalex extract paper.md
            
            # Extract from all markdown files in a directory
            pyalex extract ./papers/
            
            # Use a different model
            pyalex extract paper.md --model gpt-4
            
            # Generate interactive HTML visualization
            pyalex extract paper.md --visualize
        """
        try:
            # Check for visualization-only mode (when no input path is provided)
            if input_path is None:
                if visualize and visualize != "true":
                    # Visualization-only mode: user provided a file to --visualize
                    target_file = Path(visualize)
                    if not target_file.exists():
                        typer.echo(f"Error: Visualization file not found: {target_file}", err=True)
                        raise typer.Exit(code=1)
                    
                    typer.echo(f"Generating visualization for {target_file}...")
                    
                    # Generate HTML visualization from existing file
                    html_content = lx.visualize(str(target_file))
                    
                    # Save HTML to the same directory as the target file
                    html_output = target_file.with_suffix('.html')
                    
                    with open(html_output, "w", encoding="utf-8") as f:
                        if hasattr(html_content, 'data'):
                            f.write(html_content.data)  # For Jupyter/Colab objects
                        else:
                            f.write(html_content)
                    
                    typer.echo(f"✓ Visualization saved to {html_output}")
                    return
                else:
                    # Input path missing and no valid file for visualization
                    typer.echo("Error: Missing input path.", err=True)
                    typer.echo("Usage: pyalex extract <INPUT_PATH> [OPTIONS]", err=True)
                    typer.echo("   OR: pyalex extract --visualize <JSONL_FILE>", err=True)
                    raise typer.Exit(code=1)
            
            # Validate entity type
            if entity_type not in EXTRACTION_SCHEMAS:
                typer.echo(
                    f"Error: Unsupported entity type '{entity_type}'. "
                    f"Supported types: {', '.join(EXTRACTION_SCHEMAS.keys())}",
                    err=True
                )
                raise typer.Exit(code=1)
            
            # Resolve input path and collect markdown files
            input_p = Path(input_path)
            if not input_p.exists():
                typer.echo(f"Error: Path not found: {input_path}", err=True)
                raise typer.Exit(code=1)
            
            # Collect markdown files
            if input_p.is_dir():
                markdown_files = list(input_p.glob("**/*.md"))
                if not markdown_files:
                    typer.echo(f"Error: No markdown files found in {input_path}", err=True)
                    raise typer.Exit(code=1)
                typer.echo(f"Found {len(markdown_files)} markdown file(s) in {input_path}")
            else:
                markdown_files = [input_p]
            
            # Set default output file based on input
            if output is None:
                if input_p.is_dir():
                    output = input_p.name + ".jsonl"
                else:
                    output = input_p.stem + ".jsonl"
            
            output_path = Path(output)
            
            # Check if output already exists - skip extraction if so
            if output_path.exists():
                typer.echo(f"Output file {output_path} already exists, skipping extraction.")
                typer.echo("Use a different --output path or delete the existing file to re-extract.")
                return
            
            # Check if API key is available
            if not api_key:
                typer.echo(
                    "Warning: No OpenAI API key provided. "
                    "Set OPENAI_API_KEY environment variable or use --api-key option.",
                    err=True
                )
                raise typer.Exit(code=1)
            
            # Verify all files exist before processing
            for md_file in markdown_files:
                if not md_file.exists():
                    typer.echo(f"Error: File not found: {md_file}", err=True)
                    raise typer.Exit(code=1)
            
            # Batch process all files concurrently
            all_results, annotated_docs = extract_from_markdown_files(
                markdown_files, entity_type, model, api_key,
                max_workers=max_workers,
                extraction_pass=extraction_pass,
                enable_fuzzy_alignment=enable_fuzzy_alignment,
            )
            
            # Store annotated docs for visualization if requested
            if visualize:
                create_extract_command._annotated_docs = annotated_docs
            
            # Write results to JSONL
            typer.echo(f"\nWriting {len(all_results)} total {entity_type}(s) to {output_path}...")
            
            with open(output_path, 'w', encoding='utf-8') as f:
                for result in all_results:
                    f.write(json.dumps(result) + '\n')
            
            typer.echo(f"✓ Extraction complete! Results saved to {output_path}")
            
            # Generate visualization if requested
            if visualize and hasattr(create_extract_command, '_annotated_docs'):
                typer.echo("\nGenerating interactive HTML visualization...")
                
                # Save annotated documents to temporary JSONL for visualization
                temp_name = f"{output_path.stem}_viz.jsonl"
                lx.io.save_annotated_documents(
                    create_extract_command._annotated_docs,
                    output_name=temp_name,
                    output_dir=str(output_path.parent)
                )
                
                # Get the path to the saved file
                temp_jsonl = output_path.parent / temp_name
                
                # Generate HTML visualization
                html_content = lx.visualize(str(temp_jsonl))
                html_output = output_path.parent / f"{output_path.stem}.html"
                
                with open(html_output, "w", encoding="utf-8") as f:
                    if hasattr(html_content, 'data'):
                        f.write(html_content.data)  # For Jupyter/Colab
                    else:
                        f.write(html_content)
                
                typer.echo(f"✓ Visualization saved to {html_output}")
                
                # Clean up temporary JSONL
                if temp_jsonl.exists():
                    temp_jsonl.unlink()
                
                # Clean up the cached annotated docs
                delattr(create_extract_command, '_annotated_docs')
            
        except Exception as e:
            _handle_cli_exception(e)
