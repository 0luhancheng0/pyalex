
CUTOFF_YEAR  ?= 2017
NEG_RATIO    ?= 1
NEG_STRATEGY ?= hard_graph
PYALEX       := uv run pyalex
COLLAB_EXP   := PYTHONPATH=/Users/luhancheng/pyalex uv run python ../../collaboration_prediction.py
PYRUN_EXP    := PYTHONPATH=/Users/luhancheng/pyalex uv run python

.PHONY: all experiment figures figures-dataset figures-results clean

all: experiment

# --- Seeding: Broad Computer Science ---------------------------------------
# OpenAlex topic T11003 = Computer Science
# We fetch a larger set of seed works to approach the scale of ogbl-collab
seed_works.jsonl:
	$(PYALEX) works \
	    --topic-ids T11003 \
	    --year "2017:2018" \
	    --type article \
	    --sort-by "cited_by_count:desc" \
		--all \
	    -o $@


authors.jsonl: seed_works.jsonl
	pyalex expand --mode work_author -i seed_works.jsonl -o authors.jsonl


works.jsonl: authors.jsonl
	pyalex expand --mode author_work -i authors.jsonl -o works.jsonl --year "2017:2018"



# --- Build network ----------------------------------------------------------
network.graphml: works.jsonl
	$(PYALEX) network build \
	    -i $< \
	    -o $@ \
	    --edge-type authorship \
	    --edge-type collaboration 

embeddings.parquet: network.graphml
	$(PYALEX) embedding generate $< $@ \
	    --author-cutoff-year $(CUTOFF_YEAR) \
	    --author-aggregation-strategy mean


# --- Run experiment ---------------------------------------------------------
positive_pairs.csv negative_pairs.csv &: network.graphml
	$(COLLAB_EXP) sample \
	    $< \
	    --cutoff-year $(CUTOFF_YEAR) \
	    --neg-ratio   $(NEG_RATIO) \
	    --neg-strategy $(NEG_STRATEGY) \
	    --positive-output positive_pairs.csv \
	    --negative-output negative_pairs.csv

results.json: network.graphml embeddings.parquet positive_pairs.csv negative_pairs.csv
	$(COLLAB_EXP) evaluate $< \
	    --embeddings-file embeddings.parquet \
	    --positive-pairs positive_pairs.csv \
	    --negative-pairs negative_pairs.csv \
	    -o $@

experiment: results.json

figures: figures-dataset figures-results

figures-dataset: network.graphml positive_pairs.csv negative_pairs.csv
	$(PYRUN_EXP) ../../plot_collab_results.py dataset \
	    network.graphml \
	    --positive-pairs positive_pairs.csv \
	    --negative-pairs negative_pairs.csv \
	    --output-dir figures

figures-results: results.json
	$(PYRUN_EXP) ../../plot_collab_results.py results \
	    --results-glob "results*.json" \
	    --output-dir figures

# --- Utilities --------------------------------------------------------------
clean:
	rm -f *.jsonl *.graphml *.json *.parquet *.csv *.html
	rm -rf figures/
