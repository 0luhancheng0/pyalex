# PyAlex Embeddings Module

The `pyalex.embeddings` module provides seamless integration with [Embedding Atlas](https://apple.github.io/embedding-atlas/) for interactive visualization of OpenAlex data embeddings in Streamlit applications.

## Features

- 🎨 **Easy Visualization**: One-line function to create interactive embedding visualizations
- 🔄 **Automatic Projection**: Compute 2D projections from text automatically
- 📊 **Smart Defaults**: Pre-configured settings optimized for OpenAlex data
- 🛠️ **Flexible**: Support for custom embeddings and configurations
- 📦 **Entity Support**: Built-in helpers for Works, Authors, and Topics

## Quick Start

### Installation

```bash
pip install pyalex embedding-atlas
```

### Basic Example

```python
import streamlit as st
from pyalex import Works
from pyalex.embeddings import prepare_works_for_embeddings, pyalex_embedding_atlas

# Fetch data from OpenAlex
works = Works().search("artificial intelligence").get(limit=1000)

# Prepare for visualization
prepared = prepare_works_for_embeddings(works, text_column="abstract")

# Create interactive visualization
selection = pyalex_embedding_atlas(prepared, show_table=True)

# Handle user selection
if selection.get("predicate"):
    import duckdb
    filtered = duckdb.query_df(
        prepared, "df", 
        f"SELECT * FROM df WHERE {selection['predicate']}"
    ).df()
    st.write(f"Selected {len(filtered)} works")
```

Run with: `streamlit run app.py`

## Module Structure

```
pyalex/embeddings/
├── __init__.py           # Public API exports
├── streamlit.py          # Streamlit component wrapper
├── utils.py              # Data preparation utilities
└── README.md            # Detailed documentation
```

## API Reference

### Data Preparation Functions

#### `prepare_works_for_embeddings(df, text_column="title", additional_columns=None)`

Prepare a PyAlex works DataFrame for Embedding Atlas visualization.

**Parameters:**
- `df` (DataFrame): PyAlex works DataFrame
- `text_column` (str): Column to use as primary text (default: "title")
- `additional_columns` (list[str], optional): Extra columns to include

**Returns:** DataFrame with standardized columns ("id", "text", "label")

**Example:**
```python
from pyalex import Works
from pyalex.embeddings import prepare_works_for_embeddings

works = Works().search("machine learning").get(limit=1000)
prepared = prepare_works_for_embeddings(
    works,
    text_column="abstract",
    additional_columns=["publication_year", "cited_by_count"]
)
```

#### `prepare_authors_for_embeddings(df, text_column="display_name", additional_columns=None)`

Prepare authors DataFrame for visualization.

#### `prepare_topics_for_embeddings(df, text_column="display_name", description_column="description", additional_columns=None)`

Prepare topics DataFrame for visualization. Automatically combines display name and description for richer text embeddings.

### Visualization Component

#### `pyalex_embedding_atlas(df, text="text", compute_projection=True, ...)`

Create an Embedding Atlas Streamlit component with automatic projection.

**Key Parameters:**
- `df` (DataFrame): Prepared DataFrame with "text" column
- `text` (str): Column name for textual data
- `compute_projection` (bool): Auto-compute 2D projection if x/y not provided
- `x`, `y` (str, optional): Pre-computed projection coordinates
- `labels` (str | list): "automatic", "disabled", or custom label list
- `show_table`, `show_charts`, `show_embedding` (bool): Initial visibility

**Returns:** dict with "predicate" key containing SQL WHERE clause for selection

**Example:**
```python
selection = pyalex_embedding_atlas(
    prepared,
    text="text",
    labels="automatic",
    show_table=True,
    show_charts=True,
    key="my_atlas"
)
```

## Complete Examples

### 1. Works by Research Topic

```python
import streamlit as st
from pyalex import Works
from pyalex.embeddings import prepare_works_for_embeddings, pyalex_embedding_atlas

st.title("AI Research Explorer")

# Fetch recent AI works
works = Works().filter(
    topics={"id": "T10555"},  # Artificial Intelligence
    from_publication_date="2020-01-01"
).get(limit=5000)

# Prepare and visualize
prepared = prepare_works_for_embeddings(works, text_column="abstract")
selection = pyalex_embedding_atlas(prepared, labels="automatic")

# Show selection stats
if selection.get("predicate"):
    import duckdb
    filtered = duckdb.query_df(
        prepared, "df",
        f"SELECT * FROM df WHERE {selection['predicate']}"
    ).df()
    
    st.metric("Selected Works", len(filtered))
    st.metric("Avg Citations", f"{filtered['cited_by_count'].mean():.1f}")
```

### 2. Author Network Visualization

```python
from pyalex import Authors
from pyalex.embeddings import prepare_authors_for_embeddings, pyalex_embedding_atlas

# Top researchers in field
authors = Authors().filter(
    works_count=">100",
    cited_by_count=">1000"
).get(limit=2000)

prepared = prepare_authors_for_embeddings(
    authors,
    additional_columns=["h_index", "works_count"]
)

selection = pyalex_embedding_atlas(prepared, point_size=4)
```

### 3. Topic Landscape Explorer

```python
from pyalex import Topics
from pyalex.embeddings import prepare_topics_for_embeddings, pyalex_embedding_atlas

topics = Topics().filter(works_count=">100").get(limit=1000)

prepared = prepare_topics_for_embeddings(
    topics,
    description_column="description",
    additional_columns=["field", "domain"]
)

selection = pyalex_embedding_atlas(prepared, labels="automatic")
```

## Advanced Usage

### Custom Pre-computed Embeddings

If you have pre-computed embeddings (e.g., from OpenAI or Cohere):

```python
# Assume df has 'embedding_x' and 'embedding_y' columns
selection = pyalex_embedding_atlas(
    df,
    text="text",
    x="embedding_x",
    y="embedding_y",
    compute_projection=False  # Skip auto-projection
)
```

### Custom Labels

```python
custom_labels = [
    {"x": 0.5, "y": 0.5, "text": "AI Core", "level": 1, "priority": 10},
    {"x": -0.3, "y": 0.8, "text": "NLP", "level": 2, "priority": 5}
]

selection = pyalex_embedding_atlas(df, labels=custom_labels)
```

### Query Selection with DuckDB

```python
predicate = selection.get("predicate")
if predicate:
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

### Streamlit Community Cloud

1. Push your app to GitHub
2. Visit [share.streamlit.io](https://share.streamlit.io)
3. Connect your repository and deploy

### Local Deployment

```bash
streamlit run app.py --server.port 8501
```

## Testing

Run the test suite:

```bash
pytest tests/test_embeddings.py -v
```

The module includes comprehensive tests for:
- Data preparation utilities
- Missing value handling
- Custom column preservation
- Import error handling
- Module integration

## Performance Considerations

### Large Datasets (>10k works)

For large datasets, consider:

1. **Pagination**: Use PyAlex's efficient pagination
   ```python
   works = Works().search("query").get(limit=5000)  # Start with 5k
   ```

2. **Pre-compute Embeddings**: Compute offline for faster loading
   ```python
   # Compute once, save to disk
   prepared = prepare_works_for_embeddings(works)
   prepared.to_parquet("embeddings.parquet")
   
   # Load in Streamlit app
   prepared = pd.read_parquet("embeddings.parquet")
   ```

3. **Sampling**: For exploratory analysis
   ```python
   works_sample = works.sample(n=2000)
   prepared = prepare_works_for_embeddings(works_sample)
   ```

## Troubleshooting

### ImportError: embedding-atlas package required

**Solution:** Install the package
```bash
pip install embedding-atlas
```

### Slow Projection Computation

**Cause:** Computing embeddings for large datasets takes time

**Solutions:**
- Use smaller datasets initially (1k-5k works)
- Pre-compute embeddings offline
- Pass pre-computed `x`/`y` coordinates with `compute_projection=False`

### Memory Issues

**Cause:** Loading too many works at once

**Solutions:**
- Reduce `limit` parameter in `.get()` call
- Use PyAlex's cursor pagination for incremental loading
- Process data in batches

## Links

- [Full Documentation](pyalex/embeddings/README.md)
- [Embedding Atlas Docs](https://apple.github.io/embedding-atlas/)
- [PyAlex Documentation](https://github.com/J535D165/pyalex)
- [Example Streamlit App](examples/streamlit_example.py)
- [OpenAlex API](https://docs.openalex.org/)

## Contributing

To contribute to the embeddings module:

1. Add tests in `tests/test_embeddings.py`
2. Run tests: `pytest tests/test_embeddings.py -v`
3. Follow code style: `ruff check --fix pyalex/embeddings`
4. Format code: `ruff format pyalex/embeddings`

## License

This module is part of PyAlex and follows the same license.
