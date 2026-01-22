import asyncio
import json
import os
import re
import sys
import tempfile
import typer
import httpx
import pandas as pd
from typing import Optional

# Check for pymupdf4llm availability
try:
    import pymupdf4llm
    HAS_PYMUPDF4LLM = True
except ImportError:
    HAS_PYMUPDF4LLM = False

# Check for fitz (PyMuPDF) availability for fallback
try:
    import fitz
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False

from pyalex import Authors, Works, config

app = typer.Typer(help="Download all papers for a specific author as Markdown.")

async def convert_pdf_to_markdown(filepath: str):
    """Convert PDF to Markdown using pymupdf4llm, with fallback to basic text extraction."""
    if not HAS_PYMUPDF4LLM:
        print(f"Warning: pymupdf4llm not installed. Skipping Markdown conversion for {filepath}", file=sys.stderr)
        return

    try:
        # Run CPU-bound conversion in a separate thread
        md_text = await asyncio.to_thread(pymupdf4llm.to_markdown, filepath)
        md_path = os.path.splitext(filepath)[0] + ".md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_text)
    except Exception as e:
        # Fallback to simple text extraction if layout analysis fails (e.g. scanned PDFs or complex layouts)
        if HAS_FITZ:
            try:
                doc = fitz.open(filepath)
                text_content = []
                for page in doc:
                    text_content.append(page.get_text())
                full_text = "\n".join(text_content).strip()
                
                if full_text:
                    print(f"\nWarning: pymupdf4llm failed for {os.path.basename(filepath)}. Falling back to raw text extraction.", file=sys.stderr)
                    md_path = os.path.splitext(filepath)[0] + ".md"
                    with open(md_path, "w", encoding="utf-8") as f:
                        f.write(f"# {os.path.basename(filepath)} (Raw Text)\n\n> Note: Layout analysis failed. Displaying raw text.\n\n{full_text}")
                else:
                    print(f"\nError converting {os.path.basename(filepath)}: PDF appears to be a scanned image with no text layer.", file=sys.stderr)
            except Exception as fallback_e:
                print(f"\nError converting {filepath} to Markdown: {e}. Fallback also failed: {fallback_e}", file=sys.stderr)
        else:
            print(f"\nError converting {filepath} to Markdown: {e}", file=sys.stderr)

async def download_file(
    client: httpx.AsyncClient, 
    url: str, 
    filepath: str, 
    semaphore: asyncio.Semaphore,
    create_markdown: bool
) -> str:
    """Download a single file with concurrency control."""
    async with semaphore:
        try:
            # Check if file already exists
            if os.path.exists(filepath):
                # If PDF exists but Markdown is requested and missing, generate it
                if create_markdown:
                    md_path = os.path.splitext(filepath)[0] + ".md"
                    if not os.path.exists(md_path):
                        await convert_pdf_to_markdown(filepath)
                return "exists"

            response = await client.get(url, follow_redirects=True)
            
            if response.status_code == 200:
                # Ensure directory exists (race condition check)
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                
                with open(filepath, "wb") as f:
                    async for chunk in response.aiter_bytes():
                        f.write(chunk)
                
                if create_markdown:
                    await convert_pdf_to_markdown(filepath)
                    
                return "success"
            else:
                return f"error_{response.status_code}"
        except Exception as e:
            return f"exception_{str(e)}"

async def process_downloads(
    input_jsonl: str, 
    download_dir: str, 
    concurrency: int, 
    limit: Optional[int],
    markdown: bool,
    output_file: Optional[str] = None
):
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    print(f"Scanning {input_jsonl} for PDF URLs...")
    
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
                    
                    # Improved PDF URL extraction logic
                    pdf_url = None
                    
                    # 1. Check primary_location
                    primary_loc = data.get("primary_location")
                    if primary_loc:
                        pdf_url = primary_loc.get("pdf_url")
                    
                    # 2. Check best_oa_location if no PDF yet
                    if not pdf_url:
                        best_oa = data.get("best_oa_location")
                        if best_oa:
                            pdf_url = best_oa.get("pdf_url")
                            
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
                        safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)
                        # Remove newlines and tabs
                        safe_title = re.sub(r'[\n\t\r]', ' ', safe_title)
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
                            filename = doi.replace("https://doi.org/", "").replace("/", "_") + ".pdf"
                        elif data.get("id"):
                            # Use OpenAlex ID
                            filename = data["id"].split("/")[-1] + ".pdf"
                    
                    if filename:
                        filepath = os.path.join(download_dir, filename)
                        work_items.append((pdf_url, filepath))
                        
                except json.JSONDecodeError:
                    print(f"Warning: Skipping invalid JSON on line {i+1}", file=sys.stderr)
                    continue
                    
    except FileNotFoundError:
        print(f"Error: Input file '{input_jsonl}' not found.", file=sys.stderr)
        return

    total_files = len(work_items)
    print(f"Found {total_files} PDFs to download.")
    
    if total_files == 0:
        return

    # Configure client limits
    limits = httpx.Limits(max_keepalive_connections=concurrency, max_connections=concurrency)
    timeout = httpx.Timeout(30.0, connect=10.0)
    semaphore = asyncio.Semaphore(concurrency)
    
    print(f"Starting downloads with {concurrency} concurrent requests...")
    if markdown:
        print("Markdown conversion enabled.")
    
    async with httpx.AsyncClient(limits=limits, timeout=timeout, follow_redirects=True) as client:
        # Create tasks
        tasks = [
            download_file(client, url, filepath, semaphore, markdown) 
            for url, filepath in work_items
        ]
        
        # Track progress
        results = {"success": 0, "exists": 0, "errors": 0}
        completed = 0
        
        for future in asyncio.as_completed(tasks):
            res = await future
            completed += 1
            
            if res == "success":
                results["success"] += 1
            elif res == "exists":
                results["exists"] += 1
            else:
                results["errors"] += 1
            
            # Update progress line
            percent = (completed / total_files) * 100
            print(
                f"\rProgress: {percent:.1f}% ({completed}/{total_files}) "
                f"[Success: {results['success']} | Exists: {results['exists']} | Errors: {results['errors']}]", 
                end=""
            )

    print("\n\nDownload Summary:")
    print(f"✅ Downloaded: {results['success']}")
    print(f"⏭️  Skipped (Exists): {results['exists']}")
    print(f"❌ Errors: {results['errors']}")
    
    if output_file and markdown:
        print(f"\nConcatenating Markdown files to {output_file}...")
        try:
            with open(output_file, "w", encoding="utf-8") as outfile:
                count = 0
                for _, filepath in work_items:
                    md_path = os.path.splitext(filepath)[0] + ".md"
                    if os.path.exists(md_path):
                        try:
                            with open(md_path, "r", encoding="utf-8") as infile:
                                content = infile.read()
                                outfile.write(f"\n\n# Source: {os.path.basename(filepath)}\n\n")
                                outfile.write(content)
                                outfile.write("\n\n---\n\n")
                                count += 1
                        except Exception as e:
                            print(f"Error reading {md_path}: {e}", file=sys.stderr)
            print(f"Successfully concatenated {count} Markdown files.")
        except Exception as e:
            print(f"Error creating output file {output_file}: {e}", file=sys.stderr)

@app.command()
def main(
    input_jsonl: str = typer.Option(..., "--input-jsonl", "-i", help="Path to input JSONL file containing Works"),
    download_dir: str = typer.Option(..., "--download-dir", "-d", help="Directory to save downloaded PDFs"),
    concurrency: int = typer.Option(10, "--concurrency", "-c", help="Number of concurrent downloads"),
    limit: Optional[int] = typer.Option(None, "--limit", "-l", help="Limit number of lines to process from input file"),
    markdown: bool = typer.Option(True, "--markdown", "-m", help="Convert downloaded PDFs to Markdown"),
    output_file: Optional[str] = typer.Option(None, "--output-file", "-o", help="Concatenate all Markdown output to a single file"),
):
    """
    Download PDFs from a PyAlex Works JSONL export.
    
    Extracts 'primary_location.pdf_url' and saves files using the DOI or OpenAlex ID as the filename.
    """
    asyncio.run(process_downloads(input_jsonl, download_dir, concurrency, limit, markdown, output_file))

if __name__ == "__main__":
    app()