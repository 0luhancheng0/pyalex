"""Tests for the embeddings generator module and integration with Works."""

import pytest
import pandas as pd
from pyalex import Works


def test_works_with_embeddings_batch():
    """Test generating embeddings for a batched/paginated fetch."""
    import asyncio
    
    # Fetch 2 works to keep it fast
    df = asyncio.run(Works().search("machine learning").with_embeddings().get(limit=2))
    
    assert isinstance(df, pd.DataFrame)
    assert "embedding" in df.columns
    assert len(df) == 2
    
    # MiniLM produces 384-dimensional vectors
    emb = df.iloc[0]["embedding"]
    assert isinstance(emb, list)
    assert len(emb) == 384


def test_works_with_embeddings_single():
    """Test generating embedding for a single work ID fetch."""
    # Known ID for a highly cited paper (Attention is all you need)
    work = Works().with_embeddings()["W2741809807"]
    
    assert isinstance(work, dict)
    assert "embedding" in work
    
    emb = work["embedding"]
    assert isinstance(emb, list)
    assert len(emb) == 384


def test_generator_module_direct():
    """Test the generator directly to ensure batching works correctly."""
    from pyalex.embeddings.generator import generate_embeddings
    
    texts = ["Machine learning is fun", "Data science is cool"]
    embeddings = generate_embeddings(texts)
    
    assert len(embeddings) == 2
    assert len(embeddings[0]) == 384
    assert len(embeddings[1]) == 384
