reviews.json:
	pyalex works --topic-id T12072 --type review --year 2021 --format json --abstract --limit 50 > reviews.json

cited_by_reviews.json:
	cat reviews.json | jq "[.[].referenced_works] | flatten | unique" | pyalex works-from-ids > cited_by_reviews.json



clean:
	rm -f reviews.json cited_by_reviews.json

.PHONY: clean