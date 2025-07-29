au_funders.json:
	pyalex funders --country AU --limit 100 --json $@

au_funded_works.json: au_funders.json
	cat au_funders.json | jq 'map(.id) | unique | join(",")' | xargs pyalex works --json $@ --funder-ids

au_funded_topics.json: au_funded_works.json
	cat au_funded_works.json | jq '.[].primary_topic.display_name' > $@

wordcloud.png: au_funded_topics.json
	wordcloud_cli --text au_funded_topics.json --imagefile $@

all: au_funders.json au_funded_works.json au_funded_topics.json wordcloud.png
clean:
	rm -f au_funders.json au_funded_works.json au_funded_topics.json wordcloud.png

.PHONY: all clean
