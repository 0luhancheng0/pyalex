"""Graph utilities for the collaboration prediction experiment.

Provides helpers for:
- Parsing node attributes (year, citations, text)
- Building type and ID indices over a rustworkx graph
- Temporal graph queries (pre/post-cutoff neighbours)
"""

import itertools
from collections import defaultdict

import rustworkx as rx


def parse_year(attrs: dict) -> int:
    """Extract publication year from node attributes, defaulting to 0."""
    raw = attrs.get("year", attrs.get("publication_year", 0))
    if isinstance(raw, str):
        raw = raw.split(".")[0]  # handle "2016.0" from GraphML
    return int(float(raw or 0))


def parse_citations(attrs: dict) -> int:
    """Extract cited_by_count from node attributes, defaulting to 0."""
    raw = attrs.get("cited_by_count", 0)
    if isinstance(raw, str):
        raw = raw.split(".")[0]
    return int(float(raw or 0))


def get_text(attrs: dict) -> str:
    """Build a text string from title + abstract."""
    title = attrs.get("title", "") or ""
    abstract = attrs.get("abstract", "") or ""
    return f"{title} {abstract}".strip()


def build_indices(
    graph: rx.PyDiGraph,
) -> tuple[
    dict[str, list[int]],  # node_type -> [node_idx]
    dict[int, str],         # node_idx -> entity_id
]:
    """Index all nodes by type and build an idx-to-id map.

    Returns:
        Tuple of (type_map, idx_to_id).
    """
    type_map: dict[str, list[int]] = defaultdict(list)
    idx_to_id: dict[int, str] = {}
    for idx in graph.node_indices():
        attrs = graph.get_node_data(idx) or {}
        ntype = attrs.get("type", "unknown")
        eid = attrs.get("id", f"node_{idx}")
        type_map[ntype].append(idx)
        idx_to_id[idx] = eid
    return dict(type_map), idx_to_id


def get_pre_cutoff_works_for_author(
    graph: rx.PyDiGraph,
    author_idx: int,
    cutoff_year: int,
) -> list[int]:
    """Return node indices of works connected to *author_idx* with year <= cutoff."""
    work_indices = []
    for pred_idx in graph.predecessor_indices(author_idx):
        attrs = graph.get_node_data(pred_idx) or {}
        if attrs.get("type") != "source":
            continue
        if parse_year(attrs) <= cutoff_year:
            work_indices.append(pred_idx)
    return work_indices


def get_post_cutoff_coauthor_pairs(
    graph: rx.PyDiGraph,
    type_map: dict[str, list[int]],
    idx_to_id: dict[int, str],
    cutoff_year: int,
    eligible_authors: set[str],
) -> set[tuple[str, str]]:
    """Find eligible author pairs who co-authored a work published after cutoff.

    Args:
        graph: The full research network graph.
        type_map: Node type -> list of node indices.
        idx_to_id: Node index -> entity ID.
        cutoff_year: Only consider works published strictly after this year.
        eligible_authors: Only include author IDs in this set.

    Returns:
        Set of sorted (id_A, id_B) tuples with id_A < id_B.
    """
    pairs: set[tuple[str, str]] = set()
    for work_idx in type_map.get("source", []):
        attrs = graph.get_node_data(work_idx) or {}
        if parse_year(attrs) <= cutoff_year:
            continue
        author_ids = []
        for succ_idx in graph.successor_indices(work_idx):
            succ_attrs = graph.get_node_data(succ_idx) or {}
            if succ_attrs.get("type") == "author":
                aid = idx_to_id.get(succ_idx)
                if aid and aid in eligible_authors:
                    author_ids.append(aid)
        for a, b in itertools.combinations(sorted(author_ids), 2):
            pairs.add((a, b))
    return pairs
