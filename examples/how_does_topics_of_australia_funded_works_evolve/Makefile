funders.json:
	pyalex funders --country AU --all --json funders.json
%.json: funders.json
	cat funders.json | jq 'map(.id) | [.[] | split("/") | last] | join(",")' | xargs pyalex -d works --group-by "primary_topic.field.id" --json $@ --sort-by "count:desc" --year $* --funder-ids
clean: 
	rm -f *.json

.PHONY: clean 