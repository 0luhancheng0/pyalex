# Dataset 2: MIT CSAIL vs University of Cambridge CS
#
# Two top CS departments. Institutional seeding produces clear community labels
# while the author-expansion step picks up inter-institution collaborators.
#
# Institution OpenAlex IDs:
#   MIT CSAIL              → I136199984
#   University of Cambridge → I33216779
#
# Estimated size:
#   ~1 200 works, ~700 unique authors, runtime ~15 min.
#
# Usage:
#   make            # build everything + run experiment
#   make clean      # remove all generated files

CUTOFF_YEAR  ?= 2016
MIN_WORKS    ?= 3
NEG_RATIO    ?= 10
MODEL        ?= all-MiniLM-L6-v2
PYALEX       := uv run pyalex
COLLAB_EXP   := PYTHONPATH=/Users/luhancheng/pyalex uv run python ../../collaboration_prediction.py

MIT_ID       := I136199984
CAMBRIDGE_ID := I33216779

.PHONY: all experiment clean

all: experiment

# --- Community A: MIT CSAIL ------------------------------------------------
works_mit.jsonl:
	$(PYALEX) works \
	    --institution-ids $(MIT_ID) \
	    --year "2000:2022" \
	    --type article \
	    --sort-by "cited_by_count:desc" \
	    --limit 600 \
	    -o $@

authors_mit.jsonl: works_mit.jsonl
	$(PYALEX) expand --mode work_author -i $< --limit 200 -o $@

# Fetch additional works by MIT authors (to capture their post-cutoff output)
author_works_mit.jsonl: authors_mit.jsonl
	$(PYALEX) expand --mode author_work -i $< --limit 200 -o $@

# --- Community B: Cambridge CS ----------------------------------------------
works_cambridge.jsonl:
	$(PYALEX) works \
	    --institution-ids $(CAMBRIDGE_ID) \
	    --year "2000:2022" \
	    --type article \
	    --sort-by "cited_by_count:desc" \
	    --limit 600 \
	    -o $@

authors_cambridge.jsonl: works_cambridge.jsonl
	$(PYALEX) expand --mode work_author -i $< --limit 200 -o $@

author_works_cambridge.jsonl: authors_cambridge.jsonl
	$(PYALEX) expand --mode author_work -i $< --limit 200 -o $@

# --- Build combined network -------------------------------------------------
network.graphml: works_mit.jsonl works_cambridge.jsonl \
                 author_works_mit.jsonl author_works_cambridge.jsonl
	$(PYALEX) network build \
	    -i works_mit.jsonl \
	    -i works_cambridge.jsonl \
	    -i author_works_mit.jsonl \
	    -i author_works_cambridge.jsonl \
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
