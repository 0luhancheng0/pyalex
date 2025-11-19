from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_SPEC_NAME = "pyalex.agents.taxonomy_test_module"
_SPEC_PATH = Path(__file__).resolve().parents[1] / "pyalex" / "agents" / "taxonomy.py"
_spec = importlib.util.spec_from_file_location(_SPEC_NAME, _SPEC_PATH)
if _spec is None or _spec.loader is None:
    raise RuntimeError("Unable to load taxonomy module for testing.")
_taxonomy_module = importlib.util.module_from_spec(_spec)
sys.modules[_SPEC_NAME] = _taxonomy_module
_spec.loader.exec_module(_taxonomy_module)

TaxonomyGraph = _taxonomy_module.TaxonomyGraph


def _taxonomy_depth(categories: list[dict], depth: int = 1) -> int:
    """Return the maximum depth of a taxonomy tree (root depth = 0)."""
    if not categories:
        return depth - 1
    max_depth = depth
    for category in categories:
        sub_depth = _taxonomy_depth(category.get("subcategories") or [], depth + 1)
        max_depth = max(max_depth, sub_depth)
    return max_depth


def test_nested_block_levels_follow_taxonomy_depth() -> None:
    taxonomy = {
        "category_list": [
            {
                "name": "Systems",
                "description": "",
                "subcategories": [
                    {
                        "name": "Distributed",
                        "description": "",
                        "subcategories": [
                            {
                                "name": "Scheduling",
                                "description": "",
                                "subcategories": [],
                            }
                        ],
                    },
                    {
                        "name": "Storage",
                        "description": "",
                        "subcategories": [],
                    },
                ],
            },
            {
                "name": "Applications",
                "description": "",
                "subcategories": [],
            },
        ]
    }
    expected_depth = max(1, _taxonomy_depth(taxonomy["category_list"]))
    state = TaxonomyGraph.from_category_json(taxonomy).to_nested_block_state()
    assert len(state.get_levels()) == expected_depth
    assert state.get_levels()[-1].get_nonempty_B() == 1


def test_nested_block_levels_handle_empty_taxonomy() -> None:
    taxonomy = {"category_list": []}
    state = TaxonomyGraph.from_category_json(taxonomy).to_nested_block_state()
    assert len(state.get_levels()) == 1
    assert state.get_levels()[-1].get_nonempty_B() == 1


def test_deeper_taxonomy_adds_layers() -> None:
    shallow = {
        "category_list": [
            {
                "name": "Hardware",
                "description": "",
                "subcategories": [],
            }
        ]
    }
    deep = {
        "category_list": [
            {
                "name": "Hardware",
                "description": "",
                "subcategories": [
                    {
                        "name": "Sensors",
                        "description": "",
                        "subcategories": [
                            {
                                "name": "Optical",
                                "description": "",
                                "subcategories": [],
                            }
                        ],
                    }
                ],
            }
        ]
    }
    shallow_levels = len(TaxonomyGraph.from_category_json(shallow).to_nested_block_state().get_levels())
    deep_levels = len(TaxonomyGraph.from_category_json(deep).to_nested_block_state().get_levels())
    assert deep_levels == shallow_levels + 2


def _labels_from_property_map(prop) -> list[str]:
    graph = prop.get_graph()
    return [prop[vertex] for vertex in graph.vertices()]


def test_internal_blocks_receive_labels() -> None:
    taxonomy = {
        "category_list": [
            {
                "name": "Systems",
                "description": "",
                "subcategories": [
                    {
                        "name": "Distributed",
                        "description": "",
                        "subcategories": [
                            {
                                "name": "Scheduling",
                                "description": "",
                                "subcategories": [],
                            }
                        ],
                    }
                ],
            }
        ]
    }
    state = TaxonomyGraph.from_category_json(taxonomy).to_nested_block_state()
    vertex_text = getattr(state, "vertex_text_maps")
    assert len(vertex_text) == len(state.get_levels()) + 1
    all_labels = {
        label
        for prop in vertex_text
        for label in _labels_from_property_map(prop)
        if label
    }
    assert "Systems" in all_labels
    assert "Distributed" in all_labels


def test_long_labels_are_truncated() -> None:
    taxonomy = {
        "category_list": [
            {
                "name": "UltraLong Category Name " + "x" * 80,
                "description": "",
                "subcategories": [],
            }
        ]
    }
    graph = TaxonomyGraph.from_category_json(taxonomy)
    limit = 25
    state = graph.to_nested_block_state(max_label_chars=limit)
    vertex_text = getattr(state, "vertex_text_maps")
    base_labels = _labels_from_property_map(vertex_text[0])
    long_name = taxonomy["category_list"][0]["name"]
    prefix = long_name[: limit - 3]
    truncated_matches = [label for label in base_labels if label.startswith(prefix)]
    assert truncated_matches, "Expected category label present in base level labels"
    assert all(len(label) <= 25 for label in truncated_matches)
    assert any(label.endswith("...") for label in truncated_matches)
