help me complete the following tasks

- [] refactor the code so it always shows progress bar regardless so user know whats going on. Even if there is only 1 reqest, this should reduce the complexity of the code
- [] it seems a lot of request have `per-page=1` set, i understand this may be used for requesting the meta count but can you try optimising it by immediately start the query process? (e.g. set per-page=200 immediately so in case there are less than 10k response, this will help the performanec a bit)
- [] Improve the debugging message, it should clearly tell what decision the code is making (e.g. deciding using async vs sync, what is the effective limit, whats the batch size etc.)
- [] there still seems to be a bug in with `pyalex works --all --funder-ids` option. It does not seem to retrieve all works for large list. 