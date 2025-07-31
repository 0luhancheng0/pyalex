# Async Pyalex with Command Line Interface

This is a forked repo based on the [PyAlex](https://github.com/J535D165/pyalex) library. The two major improvements are 

1. The command line interface

```
> pyalex --help
                                                                                                                                                                                      
 Usage: pyalex [OPTIONS] COMMAND [ARGS]...                                                                                                                                            
                                                                                                                                                                                      
 CLI interface for the OpenAlex database                                                                                                                                              
                                                                                                                                                                                      
                                                                                                                                                                                      
╭─ Options ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --debug               -d               Enable debug output including API URLs and internal details                                                                                 │
│ --dry-run                              Print a list of queries that would be run without executing them                                                                            │
│ --batch-size                  INTEGER  Batch size for requests with multiple IDs (default: 100) [default: 100]                                                                     │
│ --install-completion                   Install completion for the current shell.                                                                                                   │
│ --show-completion                      Show completion for the current shell, to copy it or customize the installation.                                                            │
│ --help                                 Show this message and exit.                                                                                                                 │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ works          Search and retrieve works from OpenAlex.                                                                                                                            │
│ authors        Search and retrieve authors from OpenAlex.                                                                                                                          │
│ institutions   Search and retrieve institutions from OpenAlex.                                                                                                                     │
│ funders        Search and retrieve funders from OpenAlex.                                                                                                                          │
│ from-ids       Retrieve entities by their OpenAlex IDs from stdin.                                                                                                                 │
│ show           Display a JSON file containing OpenAlex data in table format.                                                                                                       │
│ topics         Search and retrieve topics from OpenAlex                                                                                                                            │
│ sources        Search and retrieve sources (journals/venues) from OpenAlex                                                                                                         │
│ publishers     Search and retrieve publishers from OpenAlex                                                                                                                        │
│ domains        Search and retrieve domains from OpenAlex                                                                                                                           │
│ fields         Search and retrieve fields from OpenAlex                                                                                                                            │
│ subfields      Search and retrieve subfields from OpenAlex                                                                                                                         │
│ keywords       Search and retrieve keywords from OpenAlex                                                                                                                          │
╰──────────────────────────────────────────────────────────────
```

2. Async requesting