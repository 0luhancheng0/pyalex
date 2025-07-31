funders.json:
	pyalex funders --country AU --all --json funders.json
fields.json: funders.json
	cat funders.json | jq 'map(.id) | [.[] | split("/") | last] | join(",")' | xargs pyalex works --group-by "primary_topic.field.id" --json $@ --sort-by "count:desc" --funder-ids
subfields.json: funders.json
	cat funders.json| jq 'map(.id) | [.[] | split("/") | last] | join(",")' | xargs pyalex works --group-by "primary_topic.subfield.id" --json $@ --sort-by "count:desc" --funder-ids
topics.json: funders.json
	cat funders.json| jq 'map(.id) | [.[] | split("/") | last] | join(",")' | xargs pyalex works --group-by "primary_topic.id" --json $@ --sort-by "count:desc" --funder-ids
# %_works.json: funders.json
# 	cat $< | jq 'map(.id) | unique | join(",")' | xargs pyalex works --json $@ --year $* --all --funder-ids
clean: 
	rm -f *.json

.PHONY: clean 