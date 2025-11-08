## Works CLI parity
1. Design option schema for citation, OA, venue, and abstract filters; reuse range/ID helpers.
2. Implement options and map to existing `Works.filter` calls; ensure batching covers new ID flags.
3. Extend CLI docs and add pytest cases covering each new flag (direct invocation + stdin piping).
	- Status: Completed

## Authors CLI enhancements
1. Add boolean flags for ORCID/Twitter/Wikipedia presence and ROR-based institution filters.
2. Leverage existing `_validate_and_apply_common_options` and range helpers for consistent UX.
3. Backfill tests verifying filter serialization and grouped output for `has_orcid`.
	- Status: Completed

## Broader CLI coverage
1. Scaffold commands for concepts, sources, publishers, and topics mirroring existing entity wrappers.
2. Provide shared helpers for ID list intake and pagination to minimize duplication.
3. Document new commands and wire into CLI entry points/tests before release.
	- Status: Completed
