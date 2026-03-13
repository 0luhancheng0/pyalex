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
) -> list[str]:
    """Return IDs of works published <= cutoff_year that are linked to *author_idx* via authorship edges."""
    work_ids = set()
    all_edges = list(graph.in_edges(author_idx)) + list(graph.out_edges(author_idx))
    for src_idx, tgt_idx, edge_data in all_edges:
        if (edge_data or {}).get("type") != "authorship":
            continue
        # Work is whichever end is not the author
        work_idx = src_idx if tgt_idx == author_idx else tgt_idx
        work_attrs = graph.get_node_data(work_idx) or {}
        if parse_year(work_attrs) <= cutoff_year:
            work_ids.add(work_attrs.get("id", f"node_{work_idx}"))
    return list(work_ids)


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
    authorship_found = False
    # Build work_idx -> [author_idx] for post-cutoff works only
    work_to_authors: dict[int, list[int]] = defaultdict(list)

    for edge_idx in graph.edge_indices():
        edge_data = graph.get_edge_data_by_index(edge_idx) or {}
        if edge_data.get("type") != "authorship":
            continue
        authorship_found = True
        u, v = graph.get_edge_endpoints_by_index(edge_idx)
        # Work is the non-author endpoint; author is the author endpoint
        u_type = (graph.get_node_data(u) or {}).get("type")
        v_type = (graph.get_node_data(v) or {}).get("type")
        if u_type == "author" and v_type != "author":
            author_idx, work_idx = u, v
        elif v_type == "author" and u_type != "author":
            author_idx, work_idx = v, u
        else:
            continue
        if parse_year(graph.get_node_data(work_idx) or {}) > cutoff_year:
            work_to_authors[work_idx].append(author_idx)

    if not authorship_found:
        raise ValueError(
            "No 'authorship' edges found in the graph. "
            "Rebuild with: pyalex network build --edge-type authorship"
        )

    pairs: set[tuple[str, str]] = set()
    for author_indices in work_to_authors.values():
        eligible_ids = sorted(
            eid for idx in author_indices
            if (eid := idx_to_id.get(idx)) and eid in eligible_authors
        )
        for a, b in itertools.combinations(eligible_ids, 2):
            pairs.add((a, b))

    return pairs


def get_hard_negative_candidate_pairs(
    graph: rx.PyDiGraph,
    type_map: dict[str, list[int]],
    idx_to_id: dict[int, str],
    cutoff_year: int,
    eligible_authors: set[str],
) -> list[tuple[str, str]]:
    """Find pairs of authors who share a pre-cutoff collaborator but did not collaborate pre-cutoff.

    This provides a pool of 'hard' negative candidates for link prediction,
    essential for intra-disciplinary (OGB-style) benchmarking where random 
    negatives are too easy.

    Args:
        graph: The full research network graph.
        type_map: Node type -> list of node indices.
        idx_to_id: Node index -> entity ID.
        cutoff_year: Only consider works published strictly <= this year.
        eligible_authors: Only include author IDs in this set.

    Returns:
        List of sorted (id_A, id_B) tuples with id_A < id_B.
    """
    # 1. Build pre-cutoff author-to-author adjacency via authorship edges
    authorship_found = False
    work_to_authors: dict[int, list[int]] = defaultdict(list)

    for edge_idx in graph.edge_indices():
        edge_data = graph.get_edge_data_by_index(edge_idx) or {}
        if edge_data.get("type") != "authorship":
            continue
        authorship_found = True
        u, v = graph.get_edge_endpoints_by_index(edge_idx)
        u_type = (graph.get_node_data(u) or {}).get("type")
        v_type = (graph.get_node_data(v) or {}).get("type")
        if u_type == "author" and v_type != "author":
            author_idx, work_idx = u, v
        elif v_type == "author" and u_type != "author":
            author_idx, work_idx = v, u
        else:
            continue
        if parse_year(graph.get_node_data(work_idx) or {}) <= cutoff_year:
            work_to_authors[work_idx].append(author_idx)

    if not authorship_found:
        raise ValueError(
            "No 'authorship' edges found in the graph. "
            "Rebuild with: pyalex network build --edge-type authorship"
        )

    coauthors: dict[int, set[int]] = defaultdict(set)
    for author_indices in work_to_authors.values():
        for a, b in itertools.combinations(sorted(set(author_indices)), 2):
            coauthors[a].add(b)
            coauthors[b].add(a)

    # 2. Find 2-hop neighbors that are not 1-hop neighbors
    candidates = set()

    # Pre-filter nodes mapped to eligible_authors to save time
    eligible_indices = {
        idx for idx, eid in idx_to_id.items()
        if eid in eligible_authors and graph.get_node_data(idx).get("type") == "author"
    }

    for a in eligible_indices:
        for b in coauthors[a]:  # b is a co-author of a
            for c in coauthors[b]:  # c is a co-author of b
                if c != a and c not in coauthors[a] and c in eligible_indices:
                    # a and c share a co-author but are not co-authors
                    id_a = idx_to_id[a]
                    id_c = idx_to_id[c]
                    pair = tuple(sorted([id_a, id_c]))
                    candidates.add(pair)

    return list(candidates)
