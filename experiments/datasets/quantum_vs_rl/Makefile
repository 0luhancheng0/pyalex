# Dataset 1: Quantum Computing vs Reinforcement Learning
#
# Two topically disjoint fields seeded by keyword search.
# Kept small (--limit 500 per community) to make the experiment tractable.
# The --year filter keeps pre-2024 works so we have enough post-cutoff signal.
#
# Estimated size:
#   ~1 000 works, ~600 unique authors, runtime ~10 min.
#
# Usage:
#   make            # build everything + run experiment
#   make network.graphml  # just build the graph
#   make clean      # remove all generated files

CUTOFF_YEAR  ?= 2016
MIN_WORKS    ?= 3
NEG_RATIO    ?= 10
MODEL        ?= all-MiniLM-L6-v2
PYALEX       := uv run pyalex
COLLAB_EXP   := PYTHONPATH=/Users/luhancheng/pyalex uv run python ../../collaboration_prediction.py

.PHONY: all experiment clean

all: experiment

# --- Community A: Quantum Computing ----------------------------------------
# OpenAlex topic T11417 = Quantum Computing / Quantum Information
works_quantum.jsonl:
	$(PYALEX) works \
	    --topic-ids T11417 \
	    --year "2000:2022" \
	    --type article \
	    --sort-by "cited_by_count:desc" \
	    --limit 500 \
	    -o $@

# Expand: fetch all authors that appear in quantum works
authors_quantum.jsonl: works_quantum.jsonl
	$(PYALEX) expand --mode work_author -i $< --limit 200 -o $@

author_works_quantum.jsonl: authors_quantum.jsonl
	$(PYALEX) expand --mode author_work -i $< --limit 200 -o $@

# --- Community B: Reinforcement Learning ------------------------------------
# OpenAlex topic T10290 = Reinforcement Learning
works_rl.jsonl:
	$(PYALEX) works \
	    --topic-ids T10290 \
	    --year "2000:2022" \
	    --type article \
	    --sort-by "cited_by_count:desc" \
	    --limit 500 \
	    -o $@

authors_rl.jsonl: works_rl.jsonl
	$(PYALEX) expand --mode work_author -i $< --limit 200 -o $@

author_works_rl.jsonl: authors_rl.jsonl
	$(PYALEX) expand --mode author_work -i $< --limit 200 -o $@

# --- Build combined network -------------------------------------------------
# Only authorship edges — the experiment does NOT need citation edges.
network.graphml: works_quantum.jsonl works_rl.jsonl \
                 author_works_quantum.jsonl author_works_rl.jsonl
	$(PYALEX) network build \
	    -i works_quantum.jsonl \
	    -i works_rl.jsonl \
	    -i author_works_quantum.jsonl \
	    -i author_works_rl.jsonl \
	    -o $@ \
	    --edge-type authorship

# --- Run experiment ---------------------------------------------------------
results.json: network.graphml
	$(COLLAB_EXP) prepare $< \
	    --cutoff-year $(CUTOFF_YEAR) \
	    --min-works   $(MIN_WORKS) \
	    --neg-ratio   $(NEG_RATIO) \
	    --model       $(MODEL) \
	    -o $@

experiment: results.json
	$(COLLAB_EXP) evaluate $<

# --- Utilities --------------------------------------------------------------
clean:
	rm -f *.jsonl *.graphml *.json
