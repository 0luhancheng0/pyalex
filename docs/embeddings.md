# PyAlex Embeddings & Visualization

The `pyalex.embeddings` module provides tools for generating vector representations of OpenAlex entities and visualizing them using high-performance interactive tools like Apple's [Embedding Atlas](https://apple.github.io/embedding-atlas/).

## Installation

To use the embedding and visualization features, install the required dependencies:

```bash
pip install sentence-transformers pandas pyarrow fastparquet
# And the atlas CLI for visualization
pip install embedding-atlas
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

### Generating Embeddings for Atlas

You can use the `embedding` subcommand to create a Parquet file from a network graph:

```bash
# 1. Build a network graph (copies all metadata)
pyalex network build -i works.jsonl -o network.graphml --edge-type authorship --edge-type affiliation

# 2. Generate embeddings for all entities (Works, Authors, Institutions)
pyalex embedding generate network.graphml output.parquet

# 3. Launch the interaction atlas using the standalone CLI
embedding-atlas output.parquet --vector embedding
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

1. **Lazy Loading**: PyAlex only loads ML libraries (like `sentence-transformers`) when they are actually called, keeping the base library lightweight.
2. **Metadata Flattening**: The generator automatically flattens nested OpenAlex metadata (like authorships) into JSON strings so they can be easily filtered and searched in the Atlas UI.
3. **WebGPU Support**: Embedding Atlas uses WebGPU/WebGL 2 for rendering. For large datasets (>100k points), ensure your browser supports these technologies for the best experience.
