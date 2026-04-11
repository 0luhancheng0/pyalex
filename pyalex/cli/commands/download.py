"""
Download command for PyAlex CLI.

This command allows downloading PDFs or Markdown full-text from a JSONL file containing OpenAlex Works objects.
"""

import asyncio
import json
import os
import re
import sys
from typing import Annotated
from typing import Optional

import httpx
import typer

from ..utils import _handle_cli_exception
from .help_panels import UTILITY_PANEL


async def download_file(
    client: httpx.AsyncClient,
    url: str,
    filepath: str,
    fmt: str = "pdf",
    semaphore: Optional[asyncio.Semaphore] = None,
) -> str:
    """Download a single file."""
    if semaphore is None:
        semaphore = asyncio.Semaphore(1)

    async with semaphore:
        try:
            # Check if file already exists
            if os.path.exists(filepath):
                return "exists"

            # If format is markdown, we use Jina Reader
            target_url = url
            if fmt == "markdown":
                target_url = f"https://r.jina.ai/{url}"

            response = await client.get(target_url, follow_redirects=True)

            if response.status_code == 200:
                # content-type check for PDF only
                if fmt == "pdf":
                    content_type = response.headers.get("Content-Type", "").lower()
                    if (
                        "pdf" not in content_type
                        and "application/octet-stream" not in content_type
                    ):
                        return f"skipped_content_type_{content_type}"

                # Ensure directory exists (race condition check)
                os.makedirs(os.path.dirname(filepath), exist_ok=True)

                with open(filepath, "wb") as f:
                    async for chunk in response.aiter_bytes():
                        f.write(chunk)

                return "success"
            else:
                return f"error_{response.status_code}"
        except Exception as e:
            return f"exception_{str(e)}"


async def process_downloads(
    input_jsonl: str,
    download_dir: str,
    limit: Optional[int],
    fmt: str = "pdf",
    concurrency: int = 64,
):
    """
    Process the downloads asynchronously.
    """
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    typer.echo(f"Scanning {input_jsonl} for URLs...")

    work_items = []

    # Process file line by line to avoid loading huge files into memory
    try:
        with open(input_jsonl, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if limit and i >= limit:
                    break

                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)

                    if not isinstance(data, dict):
                        continue

                    # URL extraction logic
                    target_url = None

                    if fmt == "pdf":
                        # 1. Check best_oa_location first
                        best_oa = data.get("best_oa_location")
                        if best_oa:
                            target_url = best_oa.get("pdf_url")

                        # 2. Check primary_location if no PDF yet
                        if not target_url:
                            primary_loc = data.get("primary_location")
                            if primary_loc:
                                target_url = primary_loc.get("pdf_url")

                        # 3. Check all locations if still no PDF
                        if not target_url and "locations" in data:
                            for loc in data["locations"]:
                                if loc.get("pdf_url"):
                                    target_url = loc.get("pdf_url")
                                    break
                    else:
                        # Markdown: Use landing_page_url
                        best_oa = data.get("best_oa_location")
                        if best_oa:
                            target_url = best_oa.get("landing_page_url")
                        
                        if not target_url:
                            primary_loc = data.get("primary_location")
                            if primary_loc:
                                target_url = primary_loc.get("landing_page_url")

                    if not target_url:
                        continue

                    # Determine filename: Priority DOI -> ID
                    filename = None
                    doi = data.get("doi")
                    ext = ".pdf" if fmt == "pdf" else ".md"

                    if doi:
                        # Sanitize DOI for filename
                        filename = (
                            doi.replace("https://doi.org/", "").replace("/", "_")
                            + ext
                        )
                    elif data.get("id"):
                        # Use OpenAlex ID
                        filename = data["id"].split("/")[-1] + ext

                    if filename:
                        filepath = os.path.join(download_dir, filename)
                        work_items.append((target_url, filepath))

                except json.JSONDecodeError:
                    continue

    except FileNotFoundError:
        typer.echo(f"Error: Input file '{input_jsonl}' not found.", err=True)
        return

    total_files = len(work_items)
    typer.echo(f"Found {total_files} files to download as {fmt}.")

    if total_files == 0:
        return

    # Configure client
    timeout = httpx.Timeout(60.0, connect=10.0)
    semaphore = asyncio.Semaphore(concurrency)

    typer.echo(f"Starting downloads (concurrency: {concurrency})...")
    
    async with httpx.AsyncClient(
        timeout=timeout, follow_redirects=True
    ) as client:
        # Create tasks
        tasks = [
            download_file(client, url, filepath, fmt=fmt, semaphore=semaphore)
            for url, filepath in work_items
        ]

        # Track progress
        results = {"success": 0, "exists": 0, "errors": 0, "skipped_content_type": 0}
        error_details = []
        completed = 0

        for future in asyncio.as_completed(tasks):
            res = await future
            completed += 1

            if res == "success":
                results["success"] += 1
            elif res == "exists":
                results["exists"] += 1
            elif str(res).startswith("skipped_content_type"):
                results["skipped_content_type"] += 1
            else:
                results["errors"] += 1
                error_details.append(res)

            # Update progress line
            percent = (completed / total_files) * 100
            print(
                f"\rProgress: {percent:.1f}% ({completed}/{total_files}) "
                f"[Success: {results['success']} | Exists: {results['exists']} | "
                f"Errors: {results['errors']}]",
                end="",
                flush=True
            )

    typer.echo("\n\nDownload Summary:")
    typer.echo(f"✅ Downloaded: {results['success']}")
    typer.echo(f"⏭️  Skipped (Exists): {results['exists']}")
    if fmt == "pdf":
        typer.echo(f"⏩ Skipped (Content-Type): {results['skipped_content_type']}")
    typer.echo(f"❌ Errors: {results['errors']}")

    if error_details:
        from collections import Counter
        counts = Counter(error_details)
        typer.echo("\nError breakdown (top 10):")
        for err, count in counts.most_common(10):
            typer.echo(f"  - {err}: {count}")


def create_download_command(app):
    """Create and register the download command."""

    @app.command(rich_help_panel="Utility Commands")
    def download(
        input_path: Annotated[
            Optional[str],
            typer.Argument(
                help="Path to input JSONL file containing Works",
            ),
        ] = None,
        input_opt: Annotated[
            Optional[str],
            typer.Option(
                "--input",
                "-i",
                help="Path to input JSONL file containing Works",
            ),
        ] = None,
        output_dir: Annotated[
            str,
            typer.Option(
                "--output",
                "-o",
                "--output-dir",
                help="Directory to save downloaded files",
            ),
        ] = "downloads",
        limit: Annotated[
            Optional[int],
            typer.Option(
                "--limit",
                "-l",
                help="Limit number of lines to process from input file",
            ),
        ] = None,
        fmt: Annotated[
            str,
            typer.Option(
                "--format",
                "-f",
                help="Download format: 'pdf' (direct) or 'markdown' (via Jina Reader)",
            ),
        ] = "pdf",
        concurrency: Annotated[
            int,
            typer.Option(
                "--concurrency",
                "-c",
                help="Number of concurrent downloads",
            ),
        ] = 32,
    ):
        """
        Download PDFs or full-text Markdown from a PyAlex Works JSONL export.

        For PDFs, extracts 'primary_location.pdf_url'.
        For Markdown, uses 'primary_location.landing_page_url' with Jina Reader (https://r.jina.ai/).
        """
        try:
            effective_input = input_opt or input_path
            if not effective_input:
                typer.echo("Error: Missing input file. Provide via arguments or --input.", err=True)
                raise typer.Exit(1)

            asyncio.run(
                process_downloads(
                    effective_input, 
                    output_dir, 
                    limit, 
                    fmt=fmt, 
                    concurrency=concurrency
                )
            )
        except Exception as e:
            _handle_cli_exception(e)
