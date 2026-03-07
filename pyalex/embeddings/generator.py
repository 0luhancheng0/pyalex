"""Text embedding generation utility for PyAlex."""

import functools
import logging

try:
    from pyalex.logger import get_logger

    logger = get_logger()
except ImportError:
    # Fallback if logging module is not available
    logger = logging.getLogger(__name__)


@functools.lru_cache(maxsize=2)
def _get_model(model_name: str):
    """Lazily load and cache the SentenceTransformer model."""
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        raise ImportError(
            "The 'sentence-transformers' package is required for embedding generation. "
            "Please install it with: pip install sentence-transformers"
        )
    logger.info(f"Loading embedding model: {model_name}")
    return SentenceTransformer(model_name)


def generate_embeddings(
    texts: list[str], model_name: str = "all-MiniLM-L6-v2"
) -> list[list[float]]:
    """Generate embeddings for a list of texts using the specified model.

    Parameters
    ----------
    texts : list[str]
        A list of strings to be embedded.
    model_name : str, optional
        The name of the sentence-transformers model to use, by default "all-MiniLM-L6-v2".

    Returns
    -------
    list[list[float]]
        A list of embedding vectors.
    """
    if not texts:
        return []

    model = _get_model(model_name)
    # Convert numpy arrays to lists for easier consumption and JSON serialization
    embeddings = model.encode(texts, show_progress_bar=False)
    return embeddings.tolist()
