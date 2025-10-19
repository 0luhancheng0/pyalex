"""
Utility functions for preparing PyAlex DataFrames for Embedding Atlas visualization.
"""

import pandas as pd


def prepare_works_for_embeddings(
    df: pd.DataFrame,
    text_column: str = "title",
    additional_columns: list[str] | None = None,
) -> pd.DataFrame:
    """
    Prepare a PyAlex works DataFrame for Embedding Atlas visualization.

    Args:
        df: DataFrame from PyAlex works query
        text_column: Column to use as primary text (default: "title")
        additional_columns: Extra columns to include in visualization

    Returns:
        DataFrame ready for embedding_atlas component with standardized columns

    Example:
        >>> from pyalex import Works
        >>> works = Works().search("machine learning").get(limit=1000)
        >>> prepared = prepare_works_for_embeddings(works, text_column="abstract")
    """
    result = df.copy()

    # Standard columns to keep
    keep_cols = ["id", text_column]

    # Add common useful columns if they exist
    optional_cols = [
        "publication_year",
        "cited_by_count",
        "type",
        "doi",
        "display_name",
    ]
    for col in optional_cols:
        if col in result.columns and col not in keep_cols:
            keep_cols.append(col)

    # Add user-specified columns
    if additional_columns:
        for col in additional_columns:
            if col in result.columns and col not in keep_cols:
                keep_cols.append(col)

    # Filter to available columns
    keep_cols = [c for c in keep_cols if c in result.columns]
    result = result[keep_cols]

    # Rename text column to 'text' for consistency
    if text_column != "text":
        result = result.rename(columns={text_column: "text"})

    # Handle missing text values
    result["text"] = result["text"].fillna("").astype(str)

    # Create a clean display ID
    if "display_name" in result.columns:
        result["label"] = result["display_name"]
    else:
        result["label"] = result["text"].str[:50] + "..."

    return result


def prepare_authors_for_embeddings(
    df: pd.DataFrame,
    text_column: str = "display_name",
    additional_columns: list[str] | None = None,
) -> pd.DataFrame:
    """
    Prepare a PyAlex authors DataFrame for Embedding Atlas visualization.

    Args:
        df: DataFrame from PyAlex authors query
        text_column: Column to use as primary text (default: "display_name")
        additional_columns: Extra columns to include in visualization

    Returns:
        DataFrame ready for embedding_atlas component

    Example:
        >>> from pyalex import Authors
        >>> authors = Authors().search("Einstein").get(limit=100)
        >>> prepared = prepare_authors_for_embeddings(authors)
    """
    result = df.copy()

    keep_cols = ["id", text_column]

    # Add common author columns
    optional_cols = ["works_count", "cited_by_count", "last_known_institution"]
    for col in optional_cols:
        if col in result.columns and col not in keep_cols:
            keep_cols.append(col)

    if additional_columns:
        for col in additional_columns:
            if col in result.columns and col not in keep_cols:
                keep_cols.append(col)

    keep_cols = [c for c in keep_cols if c in result.columns]
    result = result[keep_cols]

    if text_column != "text":
        result = result.rename(columns={text_column: "text"})

    result["text"] = result["text"].fillna("").astype(str)
    result["label"] = result["text"]

    return result


def prepare_topics_for_embeddings(
    df: pd.DataFrame,
    text_column: str = "display_name",
    description_column: str | None = "description",
    additional_columns: list[str] | None = None,
) -> pd.DataFrame:
    """
    Prepare a PyAlex topics DataFrame for Embedding Atlas visualization.

    Args:
        df: DataFrame from PyAlex topics query
        text_column: Column to use as primary text (default: "display_name")
        description_column: Column with topic description
        additional_columns: Extra columns to include in visualization

    Returns:
        DataFrame ready for embedding_atlas component

    Example:
        >>> from pyalex import Topics
        >>> topics = Topics().get(limit=500)
        >>> prepared = prepare_topics_for_embeddings(topics)
    """
    result = df.copy()

    keep_cols = ["id", text_column]

    # Add description if available
    if description_column and description_column in result.columns:
        keep_cols.append(description_column)

    # Add common topic columns
    optional_cols = ["works_count", "cited_by_count", "subfield", "field", "domain"]
    for col in optional_cols:
        if col in result.columns and col not in keep_cols:
            keep_cols.append(col)

    if additional_columns:
        for col in additional_columns:
            if col in result.columns and col not in keep_cols:
                keep_cols.append(col)

    keep_cols = [c for c in keep_cols if c in result.columns]
    result = result[keep_cols]

    # Combine display name and description for richer text
    if description_column and description_column in result.columns:
        result["text"] = (
            result[text_column].fillna("").astype(str)
            + ". "
            + result[description_column].fillna("").astype(str)
        )
    else:
        if text_column != "text":
            result = result.rename(columns={text_column: "text"})
        result["text"] = result["text"].fillna("").astype(str)

    result["label"] = (
        result[text_column] if text_column in result.columns else result["text"]
    )

    return result
