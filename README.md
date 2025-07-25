<p align="center">
  <img alt="PyAlex - a Python wrapper for OpenAlex" src="https://github.com/J535D165/pyalex/raw/main/pyalex_repocard.svg">
</p>

# PyAlex

![PyPI](https://img.shields.io/pypi/v/pyalex) [![DOI](https://zenodo.org/badge/557541347.svg)](https://zenodo.org/badge/latestdoi/557541347)


PyAlex is a Python library for [OpenAlex](https://openalex.org/). OpenAlex is
an index of hundreds of millions of interconnected scholarly papers, authors,
institutions, and more. OpenAlex offers a robust, open, and free [REST API](https://docs.openalex.org/) to extract, aggregate, or search scholarly data.
PyAlex is a lightweight and thin Python interface to this API. PyAlex tries to
stay as close as possible to the design of the original service.

The following features of OpenAlex are currently supported by PyAlex:

- [x] Get single entities
- [x] Filter entities
- [x] Search entities
- [x] Group entities
- [x] Search filters
- [x] Select fields
- [x] Sample
- [x] Pagination
- [x] Autocomplete endpoint
- [x] N-grams
- [x] Authentication

We aim to cover the entire API, and we are looking for help. We are welcoming Pull Requests.

## Key features

- **Pipe operations** - PyAlex can handle multiple operations in a sequence. This allows the developer to write understandable queries. For examples, see [code snippets](#code-snippets).
- **Plaintext abstracts** - OpenAlex [doesn't include plaintext abstracts](https://docs.openalex.org/api-entities/works/work-object#abstract_inverted_index) due to legal constraints. PyAlex can convert the inverted abstracts into [plaintext abstracts on the fly](#get-abstract).
- **Permissive license** - OpenAlex data is CC0 licensed :raised_hands:. PyAlex is published under the MIT license.

## Installation

PyAlex requires Python 3.8 or later.

```sh
pip install pyalex
```

## Command Line Interface

PyAlex now includes a command line interface (CLI) for quick queries to OpenAlex. After installation, you can use the `pyalex` command:

```bash
# Search for works (table format by default)
pyalex works --search "machine learning" --limit 5

# Search for authors  
pyalex authors --search "Andrew Ng" --limit 3

# Search for topics
pyalex topics --search "artificial intelligence" --limit 3

# Get specific entities by ID
pyalex works W2741809807
pyalex authors A1234567890
pyalex topics T1234567890

# Different output formats
pyalex works --search "climate change" --format json
pyalex works --search "climate change" --format title
pyalex works --search "climate change" --format table  # default
pyalex works --search "climate change" --format summary

# Filter options
pyalex works --author-id "A1234567890" --year 2023
pyalex authors --institution-id "I1234567890"
```

For more options, use the help command:

```bash
pyalex --help
pyalex works --help
pyalex authors --help  
pyalex topics --help
```

## Getting started

PyAlex offers support for all [Entity Objects](https://docs.openalex.org/api-entities/entities-overview): [Works](https://docs.openalex.org/api-entities/works), [Authors](https://docs.openalex.org/api-entities/authors), [Sources](https://docs.openalex.org/api-entities/sourcese), [Institutions](https://docs.openalex.org/api-entities/institutions), [Topics](https://docs.openalex.org/api-entities/topics), [Publishers](https://docs.openalex.org/api-entities/publishers), and [Funders](https://docs.openalex.org/api-entities/funders).

```python
from pyalex import Works, Authors, Sources, Institutions, Topics, Publishers, Funders
```

### The polite pool

[The polite pool](https://docs.openalex.org/how-to-use-the-api/rate-limits-and-authentication#the-polite-pool) has much
faster and more consistent response times. To get into the polite pool, you
set your email:

```python
import pyalex

pyalex.config.email = "mail@example.com"
```

### Max retries

By default, PyAlex will raise an error at the first failure when querying the OpenAlex API. You can set `max_retries` to a number higher than 0 to allow PyAlex to retry when an error occurs. `retry_backoff_factor` is related to the delay between two retry, and `retry_http_codes` are the HTTP error codes that should trigger a retry.

```python
from pyalex import config

config.max_retries = 0
config.retry_backoff_factor = 0.1
config.retry_http_codes = [429, 500, 503]
```

### Standards

OpenAlex uses standard [ISO_3166-1_alpha-2](https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2) country codes.

### Get single entity

Get a single Work, Author, Source, Institution, Concept, Topic, Publisher or Funder from OpenAlex by the
OpenAlex ID, or by DOI or ROR.

```python
Works()["W2741809807"]

# same as
Works()["https://doi.org/10.7717/peerj.4375"]
```

The result is a `Work` object, which is very similar to a dictionary. Find the available fields with `.keys()`.

For example, get the open access status:

```python
Works()["W2741809807"]["open_access"]
```

```python
{'is_oa': True, 'oa_status': 'gold', 'oa_url': 'https://doi.org/10.7717/peerj.4375'}
```

The previous works also for Authors, Sources, Institutions, Concepts and Topics

```python
Authors()["A5027479191"]
Authors()["https://orcid.org/0000-0002-4297-0502"]  # same
```

#### Get random

Get a [random Work, Author, Source, Institution, Concept, Topic, Publisher or Funder](https://docs.openalex.org/how-to-use-the-api/get-single-entities/random-result).

```python
Works().random()
Authors().random()
Sources().random()
Institutions().random()
Topics().random()
Publishers().random()
Funders().random()
```

Check also [sample](#sample), which does support filters.

#### Get abstract

Only for Works. Request a work from the OpenAlex database:

```python
w = Works()["W3128349626"]
```

All attributes are available like documented under [Works](https://docs.openalex.org/api-entities/works/work-object), as well as `abstract` (only if `abstract_inverted_index` is not None). This abstract made human readable is create on the fly.

```python
w["abstract"]
```

```python
'Abstract To help researchers conduct a systematic review or meta-analysis as efficiently and transparently as possible, we designed a tool to accelerate the step of screening titles and abstracts. For many tasks—including but not limited to systematic reviews and meta-analyses—the scientific literature needs to be checked systematically. Scholars and practitioners currently screen thousands of studies by hand to determine which studies to include in their review or meta-analysis. This is error prone and inefficient because of extremely imbalanced data: only a fraction of the screened studies is relevant. The future of systematic reviewing will be an interaction with machine learning algorithms to deal with the enormous increase of available text. We therefore developed an open source machine learning-aided pipeline applying active learning: ASReview. We demonstrate by means of simulation studies that active learning can yield far more efficient reviewing than manual reviewing while providing high quality. Furthermore, we describe the options of the free and open source research software and present the results from user experience tests. We invite the community to contribute to open source projects such as our own that provide measurable and reproducible improvements over current practice.'
```

Please respect the legal constraints when using this feature.

### Get lists of entities

```python
results = Works().get()
```

For lists of entities, you can also `count` the number of records found
instead of returning the results. This also works for search queries and
filters.

```python
Works().count()
# 10338153
```

For lists of entities, you can return the result as well as the metadata. By default, only the results are returned.

```python
topics = Topics().get()
```

```python
print(topics.meta)
{'count': 65073, 'db_response_time_ms': 16, 'page': 1, 'per_page': 25}
```

#### Filter records

```python
Works().filter(publication_year=2020, is_oa=True).get()
```

which is identical to:

```python
Works().filter(publication_year=2020).filter(is_oa=True).get()
```

#### Nested attribute filters

Some attribute filters are nested and separated with dots by OpenAlex. For
example, filter on [`authorships.institutions.ror`](https://docs.openalex.org/api-entities/works/filter-works).

In case of nested attribute filters, use a dict to build the query.

```python
Works()
  .filter(authorships={"institutions": {"ror": "04pp8hn57"}})
  .get()
```

#### Search entities

OpenAlex reference: [The search parameter](https://docs.openalex.org/api-entities/works/search-works)

```python
Works().search("fierce creatures").get()
```

#### Search filter

OpenAlex reference: [The search filter](https://docs.openalex.org/api-entities/works/search-works#search-a-specific-field)

```python
Authors().search_filter(display_name="einstein").get()
```

```python
Works().search_filter(title="cubist").get()
```

```python
Funders().search_filter(display_name="health").get()
```


#### Sort entity lists

OpenAlex reference: [Sort entity lists](https://docs.openalex.org/api-entities/works/get-lists-of-works#page-and-sort-works).

```python
Works().sort(cited_by_count="desc").get()
```

#### Select

OpenAlex reference: [Select fields](https://docs.openalex.org/how-to-use-the-api/get-lists-of-entities/select-fields).

```python
Works().filter(publication_year=2020, is_oa=True).select(["id", "doi"]).get()
```

#### Sample

OpenAlex reference: [Sample entity lists](https://docs.openalex.org/how-to-use-the-api/get-lists-of-entities/sample-entity-lists).

```python
Works().sample(100, seed=535).get()
```

Get 10 random German-based institutions:

```python
Institutions().filter(country_code="DE").sample(10).get()
```

Check also [random](#get-random), which does not support filters.

#### Logical expressions

OpenAlex reference: [Logical expressions](https://docs.openalex.org/how-to-use-the-api/get-lists-of-entities/filter-entity-lists#logical-expressions)

Inequality:

```python
Sources().filter(works_count=">1000").get()
```

Negation (NOT):

```python
Institutions().filter(country_code="!us").get()
```

Intersection (AND):

```python
Works().filter(institutions={"country_code": ["fr", "gb"]}).get()

# same
Works().filter(institutions={"country_code": "fr"}).filter(institutions={"country_code": "gb"}).get()
```

Addition (OR):

```python
Works().filter(institutions={"country_code": "fr|gb"}).get()
```

#### Paging

OpenAlex offers two methods for paging: [basic (offset) paging](https://docs.openalex.org/how-to-use-the-api/get-lists-of-entities/paging#basic-paging) and [cursor paging](https://docs.openalex.org/how-to-use-the-api/get-lists-of-entities/paging#cursor-paging). Both methods are supported by PyAlex.

##### Cursor paging (default)

Use the method `paginate()` to paginate results. Each returned page is a list
of records, with a maximum of `per_page` (default 25). By default,
`paginate`s argument `n_max` is set to 10000. Use `None` to retrieve all
results.

```python
from pyalex import Authors

pager = Authors().search_filter(display_name="einstein").paginate(per_page=200)

for page in pager:
    print(len(page))
```

> Looking for an easy method to iterate the records of a pager?

```python
from itertools import chain
from pyalex import Authors

query = Authors().search_filter(display_name="einstein")

for record in chain(*query.paginate(per_page=200)):
    print(record["id"])
```

##### Basic paging

See limitations of [basic paging](https://docs.openalex.org/how-to-use-the-api/get-lists-of-entities/paging#basic-paging) in the OpenAlex documentation.

```python
from pyalex import Authors

pager = Authors().search_filter(display_name="einstein").paginate(method="page", per_page=200)

for page in pager:
    print(len(page))
```


### Autocomplete

OpenAlex reference: [Autocomplete entities](https://docs.openalex.org/how-to-use-the-api/get-lists-of-entities/autocomplete-entities).

Autocomplete a string:
```python
from pyalex import autocomplete

autocomplete("stockholm resilience centre")
```

Autocomplete a string to get a specific type of entities:
```python
from pyalex import Institutions

Institutions().autocomplete("stockholm resilience centre")
```

You can also use the filters to autocomplete:
```python
from pyalex import Works

r = Works().filter(publication_year=2023).autocomplete("planetary boundaries")
```


### Get N-grams

OpenAlex reference: [Get N-grams](https://docs.openalex.org/api-entities/works/get-n-grams).


```python
Works()["W2023271753"].ngrams()
```


### Serialize

All results from PyAlex can be serialized. For example, save the results to a JSON file:

```python
import json
from pathlib import Path
from pyalex import Work

with open(Path("works.json"), "w") as f:
    json.dump(Works().get(), f)

with open(Path("works.json")) as f:
    works = [Work(w) for w in json.load(f)]
```

## Code snippets

A list of awesome use cases of the OpenAlex dataset.

### Search author by name and affiliation

This requires searching for the affiliation first, retrieving the affiliation ID, and then searching for the author while filtering for the affiliation:

```python
from pyalex import Authors, Institutions
import logging

# Search for the institution
insts = Institutions().search("MIT").get()
logging.info(f"{len(insts)} search results found for the institution")
inst_id = insts[0]["id"].replace("https://openalex.org/", "")

# Search for the author within the institution
auths = Authors().search("Daron Acemoglu").filter(affiliations={"institution":{"id": inst_id}}).get()
logging.info(f"{len(auths)} search results found for the author")
auth = auths[0]
```

### Cited publications (works referenced by this paper, outgoing citations)

```python
from pyalex import Works

# the work to extract the referenced works of
w = Works()["W2741809807"]

Works()[w["referenced_works"]]
```

### Citing publications (other works that reference this paper, incoming citations)

```python
from pyalex import Works
Works().filter(cites="W2741809807").get()
```

### Get works of a single author

```python
from pyalex import Works

Works().filter(author={"id": "A2887243803"}).get()
```

> [!WARNING]
> This gets only the first 25 works of the author. To get all of them, see the [paging section](#paging).

### Dataset publications in the global south

```python
from pyalex import Works

# the work to extract the referenced works of
w = Works() \
  .filter(institutions={"is_global_south":True}) \
  .filter(type="dataset") \
  .group_by("institutions.country_code") \
  .get()

```

### Most cited publications in your organisation

```python
from pyalex import Works

Works() \
  .filter(authorships={"institutions": {"ror": "04pp8hn57"}}) \
  .sort(cited_by_count="desc") \
  .get()

```

## Experimental

### Authentication

OpenAlex experiments with authenticated requests at the moment. Authenticate your requests with

```python
import pyalex

pyalex.config.api_key = "<MY_KEY>"
```

To check out whether your API key is indeed working, you can use the following code:

```python
import requests
pyalex.config.retry_http_codes = None
try:
    pyalex.Works().filter(from_updated_date="2023-01-12").get()
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 403:
        logging.info("API key is NOT working 🔴")
    else:
        logging.error(f"Unexpected HTTP error: {e}")
        raise
else:
    logging.info("API key is working 👍")
```

## Alternatives

R users can use the excellent [OpenAlexR](https://github.com/ropensci/openalexR) library.

## License

[MIT](/LICENSE)

## Contact

> This library is a community contribution. The authors of this Python library aren't affiliated with OpenAlex.

This library is maintained by [J535D165](https://github.com/J535D165) and [PeterLombaers](https://github.com/PeterLombaers).
Feel free to reach out with questions, remarks, and suggestions. The
[issue tracker](/issues) is a good starting point. You can also reach out via
[jonathandebruinos@gmail.com](mailto:jonathandebruinos@gmail.com).
