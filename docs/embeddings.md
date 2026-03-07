# PyAlex Embeddings & Visualization

The `pyalex.embeddings` module provides tools for generating vector representations of OpenAlex entities and visualizing them using high-performance interactive tools like Apple's [Embedding Atlas](https://apple.github.io/embedding-atlas/).

## Installation

To use the visualization features, install the optional dependencies:

```bash
pip install embedding-atlas pandas
```

## Embedding Generation

You can attach embeddings to any OpenAlex entity during retrieval. PyAlex uses `sentence-transformers` locally to generate these vectors.

### Python API

```python
from pyalex import Works

# Fetch works and generate embeddings for them
works = Works().search("machine learning").with_embeddings(model="all-MiniLM-L6-v2").get()

# Each work dictionary now contains an 'embedding' key
print(works[0]["embedding"])
```

### CLI

```bash
pyalex works --search "test" --embeddings-model all-MiniLM-L6-v2 --limit 10 -o works.jsonl
```

## Interactive Visualization (Embedding Atlas)

PyAlex integrates with Apple's `embedding-atlas` to provide a WebGPU-powered semantic map of your entities. This allows you to explore thousands (or millions) of points with real-time clustering and filtering.

### Python API (Jupyter Notebooks)

If you are working in a Jupyter notebook or Google Colab, you can render the atlas directly as a widget:

```python
from pyalex import Works, show_atlas

# Fetch data with embeddings
works = Works().search("large language models").with_embeddings().get(limit=500)

# Display the interactive atlas
show_atlas(works)
```

### CLI Command

You can launch a local visualization server from any JSONL file containing an `embedding` column:

```bash
# First, collect some data with embeddings
pyalex works --search "quantum computing" --embeddings-model all-MiniLM-L6-v2 -o quantum.jsonl

# Launch the interactive atlas
pyalex atlas visualize -i quantum.jsonl --port 8000
```

## Network Visualization (Plotly & UMAP)

If your data includes citation relationships, you can also visualize the entities as a network where the layout is determined by their semantic similarity.

```bash
# Build the network and include embeddings in the graph
pyalex network build -i quantum.jsonl -o quantum.graphml --include-embeddings

# Visualize using UMAP layout (clusters semantically similar nodes)
pyalex network visualize -i quantum.graphml -o quantum.html --layout umap
```

## Performance Tips

1. **Lazy Loading**: PyAlex only loads ML libraries (like `sentence-transformers` and `umap-learn`) when they are actually called, keeping the base library lightweight.
2. **Metadata Flattening**: `show_atlas` automatically flattens nested OpenAlex metadata (like authorships) into JSON strings so they can be easily filtered and searched in the Atlas UI.
3. **WebGPU Support**: Embedding Atlas uses WebGPU/WebGL 2 for rendering. For large datasets (>100k points), ensure your browser supports these technologies for the best experience.
