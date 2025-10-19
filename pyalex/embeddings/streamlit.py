"""
Streamlit component wrapper for Embedding Atlas with PyAlex defaults.
"""

from typing import Any

import pandas as pd

try:
    from embedding_atlas.projection import compute_text_projection
    from embedding_atlas.streamlit import embedding_atlas

    EMBEDDING_ATLAS_AVAILABLE = True
except ImportError:
    EMBEDDING_ATLAS_AVAILABLE = False


def pyalex_embedding_atlas(
    df: pd.DataFrame,
    text: str = "text",
    x: str | None = None,
    y: str | None = None,
    neighbors: str | None = None,
    compute_projection: bool = True,
    projection_x: str = "projection_x",
    projection_y: str = "projection_y",
    projection_neighbors: str = "neighbors",
    labels: str | list[dict[str, Any]] = "automatic",
    stop_words: list[str] | None = None,
    point_size: float | None = None,
    show_table: bool = True,
    show_charts: bool = True,
    show_embedding: bool = True,
    key: str | None = None,
) -> dict[str, str]:
    """
    Create an Embedding Atlas component for PyAlex data in Streamlit.

    This is a convenience wrapper around embedding_atlas.streamlit.embedding_atlas
    that handles projection computation and provides PyAlex-specific defaults.

    Args:
        df: DataFrame prepared with prepare_*_for_embeddings() utils
        text: Column name for textual data
        x: Column name for X coordinate (if already computed)
        y: Column name for Y coordinate (if already computed)
        neighbors: Column name for precomputed neighbors (if available)
        compute_projection: If True and x/y not provided, compute projection
            automatically
        projection_x: Column name to store computed X coordinates
        projection_y: Column name to store computed Y coordinates
        projection_neighbors: Column name to store computed neighbors
        labels: Label mode - "automatic", "disabled", or list of label dicts
        stop_words: Stop words for automatic label generation
        point_size: Override default point size
        show_table: Whether to display data table initially
        show_charts: Whether to display charts initially
        show_embedding: Whether to display embedding view initially
        key: Streamlit widget key

    Returns:
        Dictionary with "predicate" key containing SQL WHERE clause for
        current selection

    Example:
        >>> import streamlit as st
        >>> from pyalex import Works
        >>> from pyalex.embeddings import (
        ...     pyalex_embedding_atlas,
        ...     prepare_works_for_embeddings,
        ... )
        >>>
        >>> # Fetch and prepare data
        >>> works = Works().search("machine learning").get(limit=1000)
        >>> prepared = prepare_works_for_embeddings(works)
        >>>
        >>> # Create interactive visualization
        >>> selection = pyalex_embedding_atlas(
        ...     prepared,
        ...     text="text",
        ...     show_table=True,
        ...     show_charts=True
        ... )
        >>>
        >>> # Show selected items
        >>> if selection.get("predicate"):
        ...     import duckdb
        ...     filtered = duckdb.query_df(
        ...         prepared, "df",
        ...         f"SELECT * FROM df WHERE {selection['predicate']}"
        ...     ).df()
        ...     st.write(f"Selected {len(filtered)} items")
        ...     st.dataframe(filtered)

    Raises:
        ImportError: If embedding-atlas package is not installed
    """
    if not EMBEDDING_ATLAS_AVAILABLE:
        raise ImportError(
            "embedding-atlas package is required for this feature. "
            "Install it with: pip install embedding-atlas"
        )

    # Make a copy to avoid modifying original
    data = df.copy()

    # Compute projection if needed and requested
    if compute_projection and (x is None or y is None):
        compute_text_projection(
            data,
            text=text,
            x=projection_x,
            y=projection_y,
            neighbors=projection_neighbors,
        )
        x = projection_x
        y = projection_y
        neighbors = projection_neighbors

    # Call the embedding_atlas component
    result = embedding_atlas(
        data,
        text=text,
        x=x,
        y=y,
        neighbors=neighbors,
        labels=labels,
        stop_words=stop_words,
        point_size=point_size,
        show_table=show_table,
        show_charts=show_charts,
        show_embedding=show_embedding,
        key=key,
    )

    return result
