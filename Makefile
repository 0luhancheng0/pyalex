
# Configuration variables
# You can override these when calling make, e.g.:
#   make TOPIC_ID=T10002 START_YEAR=2018 END_YEAR=2020 all
TOPIC_ID := T12072
START_YEAR := 2015
END_YEAR := 2020
REVIEW_YEAR := 2021
OUTPUT_DIR := data
PAPERS_LIMIT := 100
REVIEWS_LIMIT := 5

# Derived variables
TIME_PERIOD := $(START_YEAR):$(END_YEAR)

# File paths
PAPERS_JSON := $(OUTPUT_DIR)/papers.json
REVIEWS_JSON := $(OUTPUT_DIR)/reviews.json
CITED_BY_REVIEWS_JSON := $(OUTPUT_DIR)/cited_by_reviews.json
TARGETS_JSON := $(OUTPUT_DIR)/targets.json

# Create output directory
$(OUTPUT_DIR):
	mkdir -p $(OUTPUT_DIR)

$(PAPERS_JSON): | $(OUTPUT_DIR)
	pyalex works --topic-id $(TOPIC_ID) --year "$(TIME_PERIOD)" --format json --limit $(PAPERS_LIMIT) > $(PAPERS_JSON)

$(REVIEWS_JSON): | $(OUTPUT_DIR)
	pyalex works --topic-id $(TOPIC_ID) --search review --year $(REVIEW_YEAR) --format json --abstract --limit $(REVIEWS_LIMIT) > $(REVIEWS_JSON)

$(CITED_BY_REVIEWS_JSON): $(REVIEWS_JSON)
	cat $(REVIEWS_JSON) | jq "[.[].referenced_works] | flatten | unique" | pyalex works-from-ids --format json > $(CITED_BY_REVIEWS_JSON)

$(TARGETS_JSON): $(CITED_BY_REVIEWS_JSON)
	cat $(CITED_BY_REVIEWS_JSON) | jq '[.[] | select((.publication_year >= $(START_YEAR)) and (.publication_year <= $(END_YEAR)))]' > $(TARGETS_JSON)

all: $(PAPERS_JSON) $(TARGETS_JSON)

# Convenience targets for displaying data
show-papers: $(PAPERS_JSON)
	python -m pyalex.cli show $(PAPERS_JSON) --format table

show-reviews: $(REVIEWS_JSON)
	python -m pyalex.cli show $(REVIEWS_JSON) --format table

show-targets: $(TARGETS_JSON)
	python -m pyalex.cli show $(TARGETS_JSON) --format table

# Show summary statistics
stats: $(PAPERS_JSON) $(REVIEWS_JSON) $(TARGETS_JSON)
	@echo "=== Dataset Statistics ==="
	@echo "Papers ($(START_YEAR)-$(END_YEAR)): $$(cat $(PAPERS_JSON) | jq '. | length') works"
	@echo "Reviews ($(REVIEW_YEAR)): $$(cat $(REVIEWS_JSON) | jq '. | length') works"
	@echo "Cited by reviews: $$(cat $(CITED_BY_REVIEWS_JSON) | jq '. | length') works"
	@echo "Target papers: $$(cat $(TARGETS_JSON) | jq '. | length') works"

clean:
	rm -rf $(OUTPUT_DIR)

.PHONY: clean all show-papers show-reviews show-targets stats