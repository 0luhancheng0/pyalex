# Taxonomy Agent Refactor Plan

## Goals
- Reduce the proliferation of bespoke Pydantic models in `pyalex/agents/taxonomy.py`.
- Make state handling for the LangGraph pipeline more natural and closer to the data we actually pass around (works, batches, merged taxonomy).
- Preserve strong typing where it adds value (external interface, JSON I/O) without over-specifying internal intermediate forms.

## Proposed Direction
1. **Introduce lightweight dataclasses for internal structures**
	- Replace `Category`/`Taxonomy` Pydantic models with `@dataclass` records for in-process manipulation.
	- Keep a single Pydantic schema (`TaxonomySchema`) dedicated to structured LLM I/O and conversion helpers between schema ↔ dataclass.

2. **Rework LangGraph `State`**
	- Use a simple `TypedDict` or dataclass focusing on `works`, `batch_taxonomies`, and `merged_taxonomy`.
	- Eliminate operator annotations; rely on explicit state transitions for list accumulation.

3. **Classification Output**
	- Collapse `WorkClassification` into a small dataclass; expose a `WorkClassificationSchema` only when returning structured responses to callers.
	- Provide conversion helpers to keep integration surfaces type-safe.

4. **Prompt + Agent Layer**
	- Centralise JSON schema definitions inside a dedicated module (e.g., `pyalex/agents/schemas.py`) to avoid circular imports and double definitions.
	- Adjust prompts to reference the schema classes directly so each agent remains stable while we refactor internals.

5. **Incremental Migration Steps**
	- [ ] Add new schema/dataclass modules and conversion helpers.
	- [ ] Update taxonomy generation to build dataclass trees and only serialise when handing to agents.
	- [ ] Refactor LangGraph state transitions to the simplified structure.
	- [ ] Adapt classification helper to the new data classes and ensure tests cover conversions.
	- [ ] Remove deprecated Pydantic models once all references migrate.

6. **Validation & Testing**
	- Extend unit tests to cover schema ↔ dataclass conversion round-trips.
	- Re-run existing integration tests (`pytest`, sample CLI run) to confirm no behavioural regressions.

## Risks & Mitigations
- **LLM output drift**: ensure schema conversion raises informative errors; add regression fixtures.
- **Inconsistent structures across modules**: create a shared `types.py` to define canonical dataclasses.
- **Timeline creep**: tackle in small PRs, prioritising the taxonomy pipeline before classification helpers.
