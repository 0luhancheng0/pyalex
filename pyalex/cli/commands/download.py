"""
Download command for PyAlex CLI.

This command allows downloading PDFs from a JSONL file containing OpenAlex Works objects.
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
) -> str:
    """Download a single file."""
    try:
        # Check if file already exists
        if os.path.exists(filepath):
            return "exists"

        response = await client.get(url, follow_redirects=True)

        if response.status_code == 200:
            # content-type check
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
):
    """
    Process the downloads asynchronously.
    """
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    typer.echo(f"Scanning {input_jsonl} for PDF URLs...")

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
                        typer.echo(
                            f"Warning: Skipping non-object data on line {i+1}: {str(data)[:50]}",
                            err=True,
                        )
                        continue

                    # Improved PDF URL extraction logic
                    pdf_url = None

                    # 1. Check best_oa_location first
                    best_oa = data.get("best_oa_location")
                    if best_oa:
                        pdf_url = best_oa.get("pdf_url")

                    # 2. Check primary_location if no PDF yet
                    if not pdf_url:
                        primary_loc = data.get("primary_location")
                        if primary_loc:
                            pdf_url = primary_loc.get("pdf_url")

                    # 3. Check all locations if still no PDF
                    if not pdf_url and "locations" in data:
                        for loc in data["locations"]:
                            if loc.get("pdf_url"):
                                pdf_url = loc.get("pdf_url")
                                break

                    if not pdf_url:
                        continue

                    # Determine filename: Priority Title -> DOI -> ID
                    filename = None
                    title = data.get("title")
                    doi = data.get("doi")

                    if title:
                        # Sanitize title for filename
                        # Replace invalid characters with underscore
                        safe_title = re.sub(r'[<>:"/\\|?*]', "_", title)
                        # Remove newlines and tabs
                        safe_title = re.sub(r"[\n\t\r]", " ", safe_title)
                        # Remove leading/trailing periods (can be issues on Windows) and spaces
                        safe_title = safe_title.strip(". ")

                        # Truncate if too long (max 200 chars to leave room for path)
                        if len(safe_title) > 200:
                            safe_title = safe_title[:200]

                        if safe_title:
                            filename = safe_title + ".pdf"

                    if not filename:
                        if doi:
                            # Sanitize DOI for filename
                            filename = (
                                doi.replace("https://doi.org/", "").replace("/", "_")
                                + ".pdf"
                            )
                        elif data.get("id"):
                            # Use OpenAlex ID
                            filename = data["id"].split("/")[-1] + ".pdf"

                    if filename:
                        filepath = os.path.join(download_dir, filename)
                        work_items.append((pdf_url, filepath))

                except json.JSONDecodeError:
                    typer.echo(
                        f"Warning: Skipping invalid JSON on line {i+1}", err=True
                    )
                    continue

    except FileNotFoundError:
        typer.echo(f"Error: Input file '{input_jsonl}' not found.", err=True)
        return

    total_files = len(work_items)
    typer.echo(f"Found {total_files} PDFs to download.")

    if total_files == 0:
        return

    # Configure client with no connection limits
    timeout = httpx.Timeout(30.0, connect=10.0)

    typer.echo(f"Starting downloads with unlimited concurrency...")
    
    async with httpx.AsyncClient(
        timeout=timeout, follow_redirects=True
    ) as client:
        # Create tasks
        tasks = [
            download_file(client, url, filepath)
            for url, filepath in work_items
        ]

        # Track progress
        results = {"success": 0, "exists": 0, "errors": 0, "skipped_content_type": 0}
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

            # Update progress line
            percent = (completed / total_files) * 100
            print(
                f"\rProgress: {percent:.1f}% ({completed}/{total_files}) "
                f"[Success: {results['success']} | Exists: {results['exists']} | "
                f"Errors: {results['errors']} | Skipped (Type): {results['skipped_content_type']}]",
                end="",
                flush=True
            )

    typer.echo("\n\nDownload Summary:")
    typer.echo(f"✅ Downloaded: {results['success']}")
    typer.echo(f"⏭️  Skipped (Exists): {results['exists']}")
    typer.echo(f"⏩ Skipped (Content-Type): {results['skipped_content_type']}")
    typer.echo(f"❌ Errors: {results['errors']}")


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
                help="Directory to save downloaded PDFs",
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
    ):
        """
        Download PDFs from a PyAlex Works JSONL export.

        Extracts 'primary_location.pdf_url' and saves files using the DOI or OpenAlex ID as the filename.
        """
        try:
            effective_input = input_opt or input_path
            if not effective_input:
                typer.echo("Error: Missing input file. Provide via arguments or --input.", err=True)
                raise typer.Exit(1)

            asyncio.run(
                process_downloads(effective_input, output_dir, limit)
            )
        except Exception as e:
            _handle_cli_exception(e)