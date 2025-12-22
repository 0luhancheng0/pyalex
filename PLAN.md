# Plan: Taxonomy Workflow Improvements

## Phase 1: Core Taxonomy Class & Tools
**Goal:** Enable granular manipulation of the taxonomy without rewriting the entire JSON.

1.  **Create `Taxonomy` Class:**
    -   Wrap `TaxonomyModel`.
    -   Implement methods: `add_node`, `remove_node`, `move_node`, `update_node`.
    -   Ensure these methods maintain tree integrity (e.g., handling orphans).
2.  **Create Manipulation Tools:**
    -   Wrap the `Taxonomy` methods as LangChain tools (`@tool`).
    -   Update `EvaluateTaxonomy` (or create `RefineTaxonomy`) to use these tools instead of the monolithic `refine_taxonomy` tool.

## Phase 2: Enhanced Generation Control
**Goal:** Give users control over the shape of the generated taxonomy.

1.  **Update `GenerateTaxonomy`:**
    -   Add `depth` and `breadth` parameters to `__init__`.
    -   Update `TAXONOMY_AGENT_SYSTEM_PROMPT` to dynamically include these constraints.
2.  **Update `State`:**
    -   Ensure configuration parameters can be passed through or stored in the state if they need to vary per run (though usually static per pipeline).

## Phase 3: Transparent & Scalable Merge
**Goal:** Handle large datasets and provide visibility into the merge process.

1.  **Refactor `MergeTaxonomy`:**
    -   Implement a `reduce` strategy:
        -   If `len(batches) > max_merge_batch`: Split into chunks.
        -   Merge chunks recursively.
    -   Alternatively, use a "base + delta" approach: Start with the first batch as the base, and merge subsequent batches into it one by one.
2.  **Add Logging:**
    -   Log which categories are being merged/renamed.

## Phase 4: Observable Pruning
**Goal:** detailed logs of what gets removed.

1.  **Update `PruneEmptyCategories`:**
    -   Add a `removed_categories` list to the return value or log output.
    -   Log the name of every category that is dropped.

## Phase 5: Integration & Testing
1.  **Update `TaxonomyPipeline`:**
    -   Wire up the new classes and tools.
2.  **Test:**
    -   Run with a small dataset to verify the new flow.
    -   Verify that the refinement agent actually uses the granular tools.
