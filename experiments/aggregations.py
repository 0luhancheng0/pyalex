"""Embedding aggregation strategies for author representation.

Each function takes a list of work embeddings plus optional metadata
(years, citation counts, texts) and returns a single author-level embedding.
All functions accept **kwargs so they can be called uniformly.
"""

import numpy as np

from pyalex.embeddings.embed import generate_embeddings

STRATEGY_NAMES = [
    "mean",
    "recency_weighted",
    "citation_weighted",
    "concat_abstracts",
    "max_pool",
]


def aggregate_mean(embeddings: list[np.ndarray], **_kwargs) -> np.ndarray:
    """Simple unweighted mean of work embeddings."""
    return np.mean(embeddings, axis=0).astype(np.float32)


def aggregate_recency_weighted(
    embeddings: list[np.ndarray],
    years: list[int],
    cutoff_year: int,
    **_kwargs,
) -> np.ndarray:
    """Weight each work by 1 / (cutoff_year - pub_year + 1).

    More recent works receive higher weight.
    """
    weights = np.array(
        [1.0 / (cutoff_year - y + 1) if y <= cutoff_year else 1.0 for y in years],
        dtype=np.float32,
    )
    weights /= weights.sum()
    return (weights[:, None] * np.stack(embeddings)).sum(axis=0).astype(np.float32)


def aggregate_citation_weighted(
    embeddings: list[np.ndarray],
    citations: list[int],
    **_kwargs,
) -> np.ndarray:
    """Weight each work by log1p(cited_by_count).

    Falls back to mean when all citation counts are zero.
    """
    weights = np.array([np.log1p(c) for c in citations], dtype=np.float32)
    total = weights.sum()
    if total == 0:
        return aggregate_mean(embeddings)
    weights /= total
    return (weights[:, None] * np.stack(embeddings)).sum(axis=0).astype(np.float32)


def aggregate_max_pool(embeddings: list[np.ndarray], **_kwargs) -> np.ndarray:
    """Element-wise maximum across all work embeddings."""
    return np.max(np.stack(embeddings), axis=0).astype(np.float32)


def aggregate_concat_abstracts(
    texts: list[str],
    model_name: str = "all-MiniLM-L6-v2",
    **_kwargs,
) -> np.ndarray | None:
    """Concatenate all work texts into one string and embed jointly.

    Returns None if the composite text is empty.
    """
    composite = " | ".join(t for t in texts if t and t.strip())
    if not composite.strip():
        return None
    result = generate_embeddings([composite], model_name=model_name)
    if result and result[0] is not None:
        return np.array(result[0], dtype=np.float32)
    return None


def compute_all_strategies(
    author_work_map: dict[str, list[str]],
    work_embeddings: dict[str, np.ndarray],
    work_texts_data: dict[str, dict],
    cutoff_year: int,
    model_name: str,
) -> dict[str, dict[str, np.ndarray]]:
    """Compute author embeddings under every aggregation strategy.

    Args:
        author_work_map: Maps author ID -> list of pre-cutoff work IDs.
        work_embeddings: Maps work ID -> embedding vector.
        work_texts_data: Maps work ID -> raw work dictionary from JSONL.
        cutoff_year: Year used for recency weighting.
        model_name: SentenceTransformer model for concat_abstracts.

    Returns:
        ``{strategy_name: {author_id: embedding}}``.
    """
    from graph_utils import parse_citations, parse_year, get_text

    results: dict[str, dict[str, np.ndarray]] = {s: {} for s in STRATEGY_NAMES}

    for author_id, work_ids in author_work_map.items():
        valid_work_ids = [wi for wi in work_ids if wi in work_embeddings and wi in work_texts_data]
        if not valid_work_ids:
            continue

        embs = [work_embeddings[wi] for wi in valid_work_ids]
        attrs_list = [work_texts_data[wi] for wi in valid_work_ids]
        years = [parse_year(a) for a in attrs_list]
        citations = [parse_citations(a) for a in attrs_list]
        texts = [get_text(a) for a in attrs_list]

        results["mean"][author_id] = aggregate_mean(embs)
        results["recency_weighted"][author_id] = aggregate_recency_weighted(
            embs, years=years, cutoff_year=cutoff_year,
        )
        results["citation_weighted"][author_id] = aggregate_citation_weighted(
            embs, citations=citations,
        )
        results["max_pool"][author_id] = aggregate_max_pool(embs)

        concat_result = aggregate_concat_abstracts(texts, model_name=model_name)
        if concat_result is not None:
            results["concat_abstracts"][author_id] = concat_result

    return results
