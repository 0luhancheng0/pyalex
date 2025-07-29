funders.json:
	pyalex funders --country AU --sample 5 --json $@

funded_works.json: funders.json
	cat funders.json | jq 'map(.id) | unique | join(",")' | xargs pyalex works --json $@ --year 2025 --all --funder-ids

funded_topics.json: funded_works.json
	cat funded_works.json | jq '.[].primary_topic.display_name' > $@

wordcloud.png: funded_topics.json
	wordcloud_cli --text funded_topics.json --imagefile $@

all: funders.json funded_works.json funded_topics.json wordcloud.png
clean:
	rm -f funders.json funded_works.json funded_topics.json wordcloud.png

.PHONY: all clean
