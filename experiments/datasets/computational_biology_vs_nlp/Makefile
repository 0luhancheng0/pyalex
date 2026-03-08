# Dataset 3: Computational Biology vs NLP
#
# Two fields with growing cross-disciplinary overlap (e.g. protein LLMs,
# genomics + transformers). Harder prediction task — communities are less
# cleanly separated so strategies need to generalise.
#
# OpenAlex topic IDs:
#   Computational Biology / Bioinformatics  → T10011
#   Natural Language Processing             → T10007
#
# Estimated size:
#   ~1 200 works, ~800 unique authors, runtime ~15 min.
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

.PHONY: all experiment clean

all: experiment

# --- Community A: Computational Biology / Bioinformatics -------------------
works_compbio.jsonl:
	$(PYALEX) works \
	    --topic-ids T10011 \
	    --year "2000:2022" \
	    --type article \
	    --sort-by "cited_by_count:desc" \
	    --limit 600 \
	    -o $@

authors_compbio.jsonl: works_compbio.jsonl
	$(PYALEX) expand --mode work_author -i $< --limit 200 -o $@

author_works_compbio.jsonl: authors_compbio.jsonl
	$(PYALEX) expand --mode author_work -i $< --limit 200 -o $@

# --- Community B: Natural Language Processing --------------------------------
works_nlp.jsonl:
	$(PYALEX) works \
	    --topic-ids T10007 \
	    --year "2000:2022" \
	    --type article \
	    --sort-by "cited_by_count:desc" \
	    --limit 600 \
	    -o $@

authors_nlp.jsonl: works_nlp.jsonl
	$(PYALEX) expand --mode work_author -i $< --limit 200 -o $@

author_works_nlp.jsonl: authors_nlp.jsonl
	$(PYALEX) expand --mode author_work -i $< --limit 200 -o $@

# --- Build combined network -------------------------------------------------
network.graphml: works_compbio.jsonl works_nlp.jsonl \
                 author_works_compbio.jsonl author_works_nlp.jsonl
	$(PYALEX) network build \
	    -i works_compbio.jsonl \
	    -i works_nlp.jsonl \
	    -i author_works_compbio.jsonl \
	    -i author_works_nlp.jsonl \
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
