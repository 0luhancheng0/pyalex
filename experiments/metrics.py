"""Evaluation metrics for the collaboration prediction experiment.

Provides:
- Negative pair sampling
- Per-strategy metric computation (AUC-ROC, AP, Precision@K, Spearman ρ)
"""

from typing import Any
import numpy as np


def sample_negative_pairs(
    eligible_authors: list[str],
    positive_pairs: set[tuple[str, str]],
    ratio: int = 10,
    seed: int = 42,
) -> list[tuple[str, str]]:
    """Sample negative (non-collaborating) author pairs.

    Args:
        eligible_authors: Pool of author IDs to sample from.
        positive_pairs: Known positive pairs to exclude.
        ratio: Number of negatives to sample per positive pair.
        seed: Random seed for reproducibility.

    Returns:
        List of (id_A, id_B) negative pairs.
    """
    rng = np.random.default_rng(seed)
    n_target = len(positive_pairs) * ratio
    all_authors = sorted(eligible_authors)
    negatives: list[tuple[str, str]] = []
    attempts = 0
    max_attempts = n_target * 20

    while len(negatives) < n_target and attempts < max_attempts:
        i, j = rng.choice(len(all_authors), size=2, replace=False)
        a, b = all_authors[min(i, j)], all_authors[max(i, j)]
        if (a, b) not in positive_pairs:
            negatives.append((a, b))
        attempts += 1

    return negatives


def sample_hard_negative_pairs(
    candidates: list[tuple[str, str]],
    positive_pairs: set[tuple[str, str]],
    n_target: int,
    seed: int = 42,
) -> list[tuple[str, str]]:
    """Sample hard negative pairs from a candidate pool.

    Args:
        candidates: List of pre-computed hard negative candidate pairs.
        positive_pairs: Known positive pairs to exclude.
        n_target: Number of negatives to sample.
        seed: Random seed for reproducibility.

    Returns:
        List of (id_A, id_B) negative pairs.
    """
    rng = np.random.default_rng(seed)
    valid_candidates = [p for p in candidates if p not in positive_pairs]
    
    if len(valid_candidates) <= n_target:
        return valid_candidates
        
    indices = rng.choice(len(valid_candidates), size=n_target, replace=False)
    return [valid_candidates[i] for i in indices]


def evaluate_strategy(
    embeddings: dict[str, np.ndarray],
    positive_pairs: set[tuple[str, str]],
    negative_pairs: list[tuple[str, str]],
    return_predictions: bool = False,
) -> dict[str, Any]:
    """Compute evaluation metrics for one embedding strategy.

    Metrics:
    - AUC-ROC: area under the ROC curve (primary metric)
    - avg_precision: average precision (area under PR curve)
    - precision_at_k: precision at K where K = number of positive pairs
    - spearman_rho: Spearman rank correlation between similarity and label
    - hits_at_10: ratio of positive edges ranked in top 10 against all negatives
    - hits_at_100: ratio of positive edges ranked in top 100 against all negatives

    Args:
        embeddings: Maps author ID -> embedding vector.
        positive_pairs: Set of (id_A, id_B) post-cutoff collaborations.
        negative_pairs: List of (id_A, id_B) non-collaborating pairs.

    Returns:
        Dict of metric name -> value.
    """
    from scipy.stats import spearmanr
    from sklearn.metrics import average_precision_score, roc_auc_score
    from sklearn.metrics.pairwise import cosine_similarity as cos_sim

    all_pairs = [(a, b, 1) for a, b in positive_pairs] + [
        (a, b, 0) for a, b in negative_pairs
    ]

    similarities = []
    labels = []
    skipped = 0
    predictions = []

    for a, b, label in all_pairs:
        if a not in embeddings or b not in embeddings:
            skipped += 1
            if return_predictions:
                predictions.append({"author_1": a, "author_2": b, "label": label, "score": None})
            continue
        sim = cos_sim(
            embeddings[a].reshape(1, -1),
            embeddings[b].reshape(1, -1),
        )[0, 0]
        similarities.append(float(sim))
        labels.append(label)
        if return_predictions:
            predictions.append({"author_1": a, "author_2": b, "label": label, "score": float(sim)})

    if not labels or sum(labels) == 0 or sum(labels) == len(labels):
        result: dict[str, Any] = {
            "auc_roc": 0.0,
            "avg_precision": 0.0,
            "precision_at_k": 0.0,
            "spearman_rho": 0.0,
            "hits_at_10": 0.0,
            "hits_at_100": 0.0,
            "n_positive": 0,
            "n_negative": 0,
            "n_pairs": 0,
            "skipped": skipped,
        }
        if return_predictions:
            result["predictions"] = predictions
        return result

    sims = np.array(similarities)
    labs = np.array(labels)

    auc = float(roc_auc_score(labs, sims))
    ap = float(average_precision_score(labs, sims))
    rho, _ = spearmanr(sims, labs)

    k = int(labs.sum())
    top_k_indices = np.argsort(sims)[::-1][:k]
    precision_at_k = float(labs[top_k_indices].mean())

    pos_sims = sims[labs == 1]
    neg_sims = sims[labs == 0]
    
    hits_10 = sum(1 for ps in pos_sims if np.sum(neg_sims >= ps) + 1 <= 10)
    hits_100 = sum(1 for ps in pos_sims if np.sum(neg_sims >= ps) + 1 <= 100)
    
    hits_at_10 = float(hits_10 / len(pos_sims)) if len(pos_sims) > 0 else 0.0
    hits_at_100 = float(hits_100 / len(pos_sims)) if len(pos_sims) > 0 else 0.0

    result: dict[str, Any] = {
        "auc_roc": round(auc, 4),
        "avg_precision": round(ap, 4),
        "precision_at_k": round(precision_at_k, 4),
        "spearman_rho": round(float(rho), 4),
        "hits_at_10": round(hits_at_10, 4),
        "hits_at_100": round(hits_at_100, 4),
        "n_positive": int(labs.sum()),
        "n_negative": int((1 - labs).sum()),
        "n_pairs": len(labs),
        "skipped": skipped,
    }

    if return_predictions:
        result["predictions"] = predictions

    return result
