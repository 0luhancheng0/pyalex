funders.json:
	pyalex funders --country AU --all --json-file funders.json  --sort-by 'cited_by_count:desc'

works.json:
	cat funders.json| jq '[map(.id) | .[] | split("/")[-1]] | join(",")' | xargs pyalex -d works --json-file works.json --all --funder-ids

clean:
	rm -f *.json
.PHONY: clean
