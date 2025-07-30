funders.json:
	pyalex funders --country AU --sample 5 --seed 1 --json funders.json

%_works.json: funders.json
	cat $< | jq 'map(.id) | unique | join(",")' | xargs pyalex works --json $@ --year $* --all --funder-ids

%_topics.json: %_works.json
	cat $< | jq '[.[].primary_topic.display_name]' > $*_topics.json

clean:
	rm -f *_topics.json

.PHONY: clean
.PRECIOUS: %_works.json %_topics.json