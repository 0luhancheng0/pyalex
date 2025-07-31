funders.json:
	pyalex funders --country AU --all --json funders.json

%_works.json: funders.json
	cat $< | jq 'map(.id) | unique | join(",")' | xargs pyalex works --json $@ --year $* --all --funder-ids

