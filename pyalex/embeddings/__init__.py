"""
PyAlex Embeddings Module

Integration with Embedding Atlas for visualization of OpenAlex data embeddings.
Provides helpers for Streamlit apps and data preparation utilities.
"""

from pyalex.embeddings.streamlit import pyalex_embedding_atlas
from pyalex.embeddings.utils import prepare_authors_for_embeddings
from pyalex.embeddings.utils import prepare_topics_for_embeddings
from pyalex.embeddings.utils import prepare_works_for_embeddings

__all__ = [
    "pyalex_embedding_atlas",
    "prepare_works_for_embeddings",
    "prepare_authors_for_embeddings",
    "prepare_topics_for_embeddings",
]
