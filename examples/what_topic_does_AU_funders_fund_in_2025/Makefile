funders.json:
	pyalex funders --country AU --limit 5 --json funders.json

%_works.json: funders.json
	cat funders.json | jq 'map(.id) | unique | join(",")' | xargs pyalex works --json $@ --year $* --all --funder-ids

topics.json: works.json
	cat works.json | jq '.[].primary_topic.display_name' > topics.json

wordcloud.png: topics.json
	wordcloud_cli --text topics.json --imagefile wordcloud.png --width 800 --height 400 --background white --max_words 100

all: funders.json works.json topics.json wordcloud.png
clean:
	rm -f funders.json works.json topics.json wordcloud.png

.PHONY: all clean
