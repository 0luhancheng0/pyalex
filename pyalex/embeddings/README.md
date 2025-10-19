# PyAlex Embeddings Module

Integration with [Embedding Atlas](https://apple.github.io/embedding-atlas/) for interactive visualization of OpenAlex data embeddings in Streamlit apps.

## Installation

```bash
pip install pyalex embedding-atlas
```

## Quick Start

### Basic Streamlit App

```python
import streamlit as st
from pyalex import Works
from pyalex.embeddings import pyalex_embedding_atlas, prepare_works_for_embeddings

st.title("OpenAlex Works Explorer")

# Fetch data
works = Works().search("artificial intelligence").get(limit=1000)

# Prepare for visualization
prepared = prepare_works_for_embeddings(works, text_column="abstract")

# Create interactive visualization
selection = pyalex_embedding_atlas(
    prepared,
    text="text",
    show_table=True,
    show_charts=True
)

# Show selection details
if selection.get("predicate"):
    import duckdb
    filtered = duckdb.query_df(
        prepared, "df",
        f"SELECT * FROM df WHERE {selection['predicate']}"
    ).df()
    st.write(f"✓ Selected {len(filtered)} works")
    st.dataframe(filtered[["label", "publication_year", "cited_by_count"]])
```

Run with: `streamlit run app.py`

## API Reference

### Data Preparation Functions

#### `prepare_works_for_embeddings()`

Prepare works DataFrame for Embedding Atlas visualization.

```python
from pyalex.embeddings import prepare_works_for_embeddings

prepared = prepare_works_for_embeddings(
    df,
    text_column="abstract",  # or "title"
    additional_columns=["open_access.is_oa", "keywords"]
)
```

**Parameters:**
- `df` (DataFrame): PyAlex works DataFrame
- `text_column` (str): Column to use as primary text (default: "title")
- `additional_columns` (list[str], optional): Extra columns to include

**Returns:** DataFrame with standardized columns for Embedding Atlas

#### `prepare_authors_for_embeddings()`

Prepare authors DataFrame for visualization.

```python
from pyalex.embeddings import prepare_authors_for_embeddings

prepared = prepare_authors_for_embeddings(
    df,
    text_column="display_name",
    additional_columns=["h_index"]
)
```

#### `prepare_topics_for_embeddings()`

Prepare topics DataFrame for visualization.

```python
from pyalex.embeddings import prepare_topics_for_embeddings

prepared = prepare_topics_for_embeddings(
    df,
    text_column="display_name",
    description_column="description",
    additional_columns=["field", "domain"]
)
```

### Visualization Component

#### `pyalex_embedding_atlas()`

Create an Embedding Atlas Streamlit component with automatic projection.

```python
from pyalex.embeddings import pyalex_embedding_atlas

selection = pyalex_embedding_atlas(
    df,
    text="text",
    compute_projection=True,  # Auto-compute if x/y not provided
    show_table=True,
    show_charts=True,
    show_embedding=True,
    labels="automatic",  # or "disabled" or custom list
    key="my_atlas"
)
```

**Parameters:**
- `df` (DataFrame): Prepared DataFrame
- `text` (str): Column with text data (default: "text")
- `x`, `y` (str, optional): Pre-computed projection columns
- `compute_projection` (bool): Auto-compute projection if x/y missing (default: True)
- `projection_x`, `projection_y`, `projection_neighbors` (str): Output column names
- `labels` (str | list): "automatic", "disabled", or custom label list
- `stop_words` (list[str], optional): Words to exclude from automatic labels
- `point_size` (float, optional): Point size override
- `show_table`, `show_charts`, `show_embedding` (bool): Initial visibility
- `key` (str, optional): Streamlit widget key

**Returns:** `dict` with `"predicate"` key containing SQL WHERE clause for selection

## Complete Examples

### Works by Topic

```python
import streamlit as st
from pyalex import Works
from pyalex.embeddings import pyalex_embedding_atlas, prepare_works_for_embeddings

st.title("AI Research by Topic")

# Fetch recent AI works
works = Works().filter(
    topics={"id": "T10555"},  # Artificial Intelligence topic
    from_publication_date="2020-01-01"
).get(limit=5000)

# Prepare with abstract text
prepared = prepare_works_for_embeddings(
    works,
    text_column="abstract",
    additional_columns=["topics.display_name", "keywords"]
)

# Visualize with automatic labels
selection = pyalex_embedding_atlas(
    prepared,
    labels="automatic",
    show_table=False,
    show_charts=True
)

if selection.get("predicate"):
    st.subheader("Selection Details")
    import duckdb
    filtered = duckdb.query_df(
        prepared, "df",
        f"SELECT * FROM df WHERE {selection['predicate']}"
    ).df()
    st.metric("Selected Works", len(filtered))
    st.dataframe(filtered)
```

### Author Network Visualization

```python
import streamlit as st
from pyalex import Authors
from pyalex.embeddings import pyalex_embedding_atlas, prepare_authors_for_embeddings

st.title("Researcher Network")

# Top authors in domain
authors = Authors().filter(
    works_count=">100",
    cited_by_count=">1000"
).get(limit=2000)

prepared = prepare_authors_for_embeddings(
    authors,
    additional_columns=["h_index", "works_count", "topics"]
)

selection = pyalex_embedding_atlas(
    prepared,
    point_size=4,
    show_table=True
)
```

### Topic Explorer

```python
import streamlit as st
from pyalex import Topics
from pyalex.embeddings import pyalex_embedding_atlas, prepare_topics_for_embeddings

st.title("Research Topic Landscape")

topics = Topics().filter(works_count=">100").get(limit=1000)

prepared = prepare_topics_for_embeddings(
    topics,
    description_column="description",
    additional_columns=["field", "domain", "subfield"]
)

selection = pyalex_embedding_atlas(
    prepared,
    labels="automatic",
    show_embedding=True,
    show_charts=True
)
```

## Advanced Usage

### Custom Pre-computed Embeddings

If you have pre-computed embeddings (e.g., from OpenAI, Cohere), skip projection:

```python
# Assume df has 'embedding_x' and 'embedding_y' columns
selection = pyalex_embedding_atlas(
    df,
    text="text",
    x="embedding_x",
    y="embedding_y",
    compute_projection=False  # Use existing coordinates
)
```

### Custom Labels

```python
# Define specific labels
custom_labels = [
    {"x": 0.5, "y": 0.5, "text": "AI Core", "level": 1, "priority": 10},
    {"x": -0.3, "y": 0.8, "text": "NLP", "level": 2, "priority": 5}
]

selection = pyalex_embedding_atlas(
    df,
    labels=custom_labels,
    show_table=True
)
```

### Query Selection with DuckDB

```python
import duckdb

predicate = selection.get("predicate")
if predicate:
    # Complex query on selection
    query = f"""
    SELECT 
        publication_year,
        COUNT(*) as count,
        AVG(cited_by_count) as avg_citations
    FROM df 
    WHERE {predicate}
    GROUP BY publication_year
    ORDER BY publication_year
    """
    stats = duckdb.query_df(df, "df", query).df()
    st.bar_chart(stats.set_index("publication_year")["count"])
```

## Deployment

Deploy to Streamlit Community Cloud:

1. Push code to GitHub
2. Visit [share.streamlit.io](https://share.streamlit.io)
3. Connect repository and deploy

Or deploy locally:

```bash
streamlit run app.py --server.port 8501
```

## Troubleshooting

**Import Error:**
```
ImportError: embedding-atlas package is required
```
Solution: `pip install embedding-atlas`

**Slow Projection:**
For large datasets (>10k items), consider:
- Pre-computing embeddings offline
- Sampling data before visualization
- Using cursor pagination for large queries

**Memory Issues:**
For very large datasets, use pagination:
```python
# Fetch in chunks
works = Works().search("query").get(limit=5000)  # Start with 5k
```

## Links

- [Embedding Atlas Documentation](https://apple.github.io/embedding-atlas/)
- [PyAlex Documentation](https://github.com/J535D165/pyalex)
- [OpenAlex API](https://docs.openalex.org/)
