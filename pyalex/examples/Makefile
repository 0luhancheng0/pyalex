funders.json:
	pyalex funders --country AU --all --json-file funders.json  --sort-by 'cited_by_count:desc'

works.json:
	cat funders.json| jq 'map(.id) | join(",")' | xargs pyalex -d works --json-file works.json --limit 1000 --funder-ids

clean:
	rm -f *.json
.PHONY: clean
