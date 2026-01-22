# Example Makefile for downloading author papers using PyAlex CLI

AUTHOR_NAME ?= "Yann LeCun"
AUTHOR_ID ?= ""
OUTPUT_DIR ?= "downloads"
CONCAT_FILE ?= "all_papers.md"

.PHONY: help search-author download-works process-downloads clean

help:
	@echo "PyAlex Download Utilities"
	@echo "========================="
	@echo "Usage:"
	@echo "  make search-author AUTHOR_NAME='Yann LeCun'"
	@echo "      Search for an author and display their ID."
	@echo ""
	@echo "  make download-works AUTHOR_ID='A5001226970'"
	@echo "      Fetch all works for the given Author ID to 'works.jsonl'."
	@echo ""
	@echo "  make process-downloads"
	@echo "      Download PDFs from 'works.jsonl' to '$(OUTPUT_DIR)' and concatenate to '$(CONCAT_FILE)'."
	@echo ""
	@echo "  make all AUTHOR_ID='A5001226970'"
	@echo "      Run fetch and download steps."

search-author:
	@echo "Searching for $(AUTHOR_NAME)..."
	uv run pyalex authors --search "$(AUTHOR_NAME)" --limit 5 --select id,display_name,works_count

download-works:
	@if [ -z "$(AUTHOR_ID)" ]; then echo "Error: AUTHOR_ID is undefined. Run 'make search-author' to find one."; exit 1; fi
	@echo "Fetching works for Author ID: $(AUTHOR_ID)..."
	uv run pyalex works --author-ids "$(AUTHOR_ID)" --jsonl-file works.jsonl --select id,doi,title,primary_location,best_oa_location,locations

process-downloads:
	@if [ ! -f works.jsonl ]; then echo "Error: works.jsonl not found. Run 'make download-works' first."; exit 1; fi
	@echo "Downloading PDFs to $(OUTPUT_DIR)..."
	uv run python -m pyalex.scripts.download_pdfs --input-jsonl works.jsonl --download-dir $(OUTPUT_DIR) --markdown --output-file $(CONCAT_FILE)

all: download-works process-downloads

clean:
	rm -f works.jsonl $(CONCAT_FILE)
