"""
Visualization utilities for PyAlex entities using Embedding Atlas.
"""

import json
import pandas as pd

try:
    from embedding_atlas.widget import EmbeddingAtlasWidget
    HAS_ATLAS = True
except ImportError:
    HAS_ATLAS = False


def show_atlas(entities):
    """
    Display an interactive Embedding Atlas widget for the given entities.
    
    Args:
        entities: A list of entity dictionaries (e.g., from Works().get())
                  or a Pandas DataFrame containing an 'embedding' column.
    """
    if not HAS_ATLAS:
        print("Error: embedding-atlas is not installed.")
        print("Please install it with: pip install embedding-atlas")
        return None

    if isinstance(entities, list):
        df = pd.DataFrame(entities)
    elif isinstance(entities, pd.DataFrame):
        df = entities.copy()
    else:
        raise ValueError("entities must be a list of dictionaries or a Pandas DataFrame")

    if df.empty:
        print("Warning: The provided data is empty.")
        return None

    if "embedding" not in df.columns:
        print("Error: 'embedding' column not found in data.")
        return None

    # Flatten complex metadata for visualization
    for col in df.columns:
        if col != "embedding" and df[col].apply(lambda x: isinstance(x, (list, dict))).any():
            df[col] = df[col].apply(lambda x: json.dumps(x) if isinstance(x, (list, dict)) else x)

    return EmbeddingAtlasWidget(df)
