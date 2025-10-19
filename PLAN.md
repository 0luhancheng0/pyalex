# Refactoring Implementation Plan

**Created:** October 19, 2025  
**Last Updated:** October 19, 2025  
**Current Phase:** Phase 2 - base.py.__getitem__ Dispatch Pattern

---

## Current Task: Refactor `base.py.__getitem__` Dispatch Pattern ✅ COMPLETED

### Objective
Replace the deeply nested conditional logic in `BaseOpenAlex.__getitem__` with a clean dispatch pattern that separates concerns and improves maintainability.

### ✅ Implementation Completed

**Status:** COMPLETED (October 19, 2025)

**Changes Made:**
1. ✅ Refactored `__getitem__` to use dispatch pattern (37 lines, down from 43)
2. ✅ Extracted `_handle_list_id` method (28 lines)
3. ✅ Extracted `_handle_string_id` method (17 lines)
4. ✅ Extracted `_handle_slice_id` method (43 lines)
5. ✅ Added comprehensive docstrings to all methods
6. ✅ Improved error messages with better type information

**Results:**
- Main `__getitem__` method reduced to clean 37-line dispatcher
- All logic separated into focused handler methods
- Total of 125 lines for all __getitem__ functionality (including docstrings)
- All existing tests pass ✅
- Manual testing confirms all access patterns work correctly ✅
- Code formatted and lint-checked ✅

**Code Quality Improvements:**
- **Separation of Concerns:** Each ID type has its own handler method
- **Readability:** Clear dispatch logic, no nested conditionals
- **Maintainability:** Easy to add new ID type handlers
- **Testability:** Each handler can be tested independently
- **Documentation:** Complete docstrings for all methods

**Testing Verified:**
- ✅ Single string ID: `Works()['W2741809807']`
- ✅ List of IDs: `Works()[['W123', 'W456']]`
- ✅ Slice notation: `Works()[:5]`
- ✅ Invalid type error handling
- ✅ Invalid slice parameter validation
- ✅ All pytest tests pass

---

## Next Task Queue (After base.py.__getitem__)

### Task 3: Extract CLI Command Boilerplate

**Objective:** Create `CommandExecutor` base class to eliminate repetitive command setup code

**Files to Modify:**
- Create: `pyalex/cli/command_patterns.py`
- Refactor: `pyalex/cli/commands/works.py`
- Refactor: `pyalex/cli/commands/authors.py`
- Refactor: `pyalex/cli/commands/institutions.py`
- Refactor: `pyalex/cli/commands/funders.py`

**Implementation Steps:**
1. Analyze common patterns in command files
2. Design `CommandExecutor` base class
3. Implement shared methods: `_setup_query()`, `_apply_filters()`, `_execute_query()`, `_format_output()`
4. Refactor works.py to use CommandExecutor
5. Verify works command still functions correctly
6. Refactor remaining command files
7. Remove duplicate code
8. Test all commands

**Expected Impact:** Save ~400 lines, improve command consistency

---

### Task 4: Simplify `_output_table` Using Factory Pattern

**Objective:** Replace large if/elif chain with entity-specific formatter classes

**Implementation Steps:**
1. Create `pyalex/cli/formatters.py` module
2. Design `TableFormatterFactory` and base `TableFormatter` class
3. Implement entity-specific formatters (WorksTableFormatter, AuthorsTableFormatter, etc.)
4. Update `cli/utils.py` to use factory
5. Test table output for each entity type

**Expected Impact:** Reduce `_output_table` from ~200 lines to ~30 lines

---

### Task 5: Centralize Entity Type Detection

**Objective:** Create unified entity type detection to replace multiple detection points

**Implementation Steps:**
1. Create `pyalex/core/entity_detection.py`
2. Implement `EntityTypeDetector` with signature-based detection
3. Replace detection logic in `cli/utils.py`
4. Replace detection logic in `cli/batch.py`
5. Replace detection logic in entity base classes
6. Test detection accuracy

**Expected Impact:** Single source of truth for entity type detection, easier to maintain

---

## Progress Tracking

### Completed
- ✅ **Phase 1:** RangeFilterMixin implementation (~420 lines saved)

### In Progress
- 🔄 **Phase 2:** base.py.__getitem__ dispatch pattern refactoring

### Planned
- 📋 **Phase 3:** CLI command boilerplate extraction
- 📋 **Phase 4:** Table formatter factory pattern
- 📋 **Phase 5:** Entity type detection centralization
- 📋 **Phase 6:** Pandas vectorization for batch operations
- 📋 **Phase 7:** Progress tracking context manager
- 📋 **Phase 8:** Validation.py simplification

---

## Notes & Decisions

### Design Decisions Log

**Decision 1: Mixin vs Inheritance for RangeFilterMixin**
- **Date:** 2025-10-19
- **Decision:** Use mixin pattern (multiple inheritance)
- **Rationale:** Allows entity classes to inherit from both BaseOpenAlex and RangeFilterMixin without deep hierarchy
- **Result:** ✅ Works well, all tests passing

**Decision 2: Dispatch Pattern for __getitem__**
- **Date:** 2025-10-19
- **Decision:** Use handler registry dict instead of strategy pattern
- **Rationale:** Simpler, more Pythonic, easier to extend
- **Implementation:** Handler methods registered in dict, dispatched by type detection

### Open Questions

**Q1:** Should we create a separate `IDTypeDetector` class or keep it as a method?
- **Lean toward:** Keep as private method for now, can extract later if reused elsewhere

**Q2:** Should handler methods return raw data or Entity objects?
- **Lean toward:** Keep current behavior (return Entity objects for consistency)

**Q3:** How to handle edge cases in list handler (empty list, None values)?
- **Decision:** Early return for empty list, raise ValueError for None values in list

---

## Risk Management

### Identified Risks

**Risk 1: Breaking existing functionality during refactoring**
- **Mitigation:** Thorough manual testing + run full test suite after each change
- **Fallback:** Git allows easy revert if issues found

**Risk 2: Performance regression from dispatch overhead**
- **Mitigation:** Handler lookup is O(1), should be negligible vs API calls
- **Monitoring:** Manual performance testing with large lists

**Risk 3: Missing edge cases in type detection**
- **Mitigation:** Comprehensive manual testing with various ID formats
- **Fallback:** Add specific handling if edge cases discovered

### Rollback Plan

If refactoring causes issues:
1. Revert changes: `git restore pyalex/entities/base.py`
2. Document what went wrong
3. Revise approach in this plan
4. Try again with adjusted strategy

---

## Metrics & Goals

### Code Quality Metrics

**Before Refactoring (base.py.__getitem__):**
- Lines of code: ~130
- Cyclomatic complexity: ~15
- Nested depth: 5+ levels
- Number of concerns mixed: 4+

**After Refactoring (Target):**
- Lines of code: <30 (main method)
- Cyclomatic complexity: <5 (main method)
- Nested depth: 2 levels max
- Number of concerns: 1 per method

**Overall Project (After All Tasks):**
- Total lines saved: ~1,000+
- Maintenance burden reduction: ~50%
- Test coverage increase: +15%
- Code readability score: Significant improvement

---

## Timeline Estimates

**Phase 2 (base.py refactoring):** 2-3 hours
- Analysis: 30 min
- Implementation: 1.5 hours
- Testing: 45 min
- Cleanup: 15 min

**Phase 3 (CLI boilerplate):** 3-4 hours
**Phase 4 (Table formatters):** 2-3 hours
**Phase 5 (Entity detection):** 1-2 hours

**Total estimated time:** 10-15 hours of focused work
