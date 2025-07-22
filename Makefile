
papers.json:
	pyalex works --topic-id T12072  --year "2015:2020" --format json --limit 100 > papers.json

reviews.json:
	pyalex works --topic-id T12072 --search review --year 2021 --format json --abstract --limit 5 > reviews.json

cited_by_reviews.json: reviews.json
	cat reviews.json | jq "[.[].referenced_works] | flatten | unique" | pyalex works-from-ids --format json > cited_by_reviews.json

targets.json: cited_by_reviews.json
	cat cited_by_reviews.json | jq '[.[] | select((.publication_year >= 2015) and (.publication_year <= 2020))]' > targets.json

all: papers.json targets.json

clean:
	rm -f *.json

.PHONY: clean all