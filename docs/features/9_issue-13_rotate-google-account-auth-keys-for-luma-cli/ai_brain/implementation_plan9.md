# Implementation Plan - Preserve Version in ROADMAP.md

Luma CLI currently overwrites the status column or line in `ROADMAP.md` when an issue is updated (either automatically for closed issues or manually via `action_update_roadmap`). This causes existing version strings (e.g., `(v0.5.0)`) or notes to be lost if they aren't re-entered.

## Proposed Changes

### [Component] Luma Core Actions

#### [MODIFY] [quality_actions.py](file:///Users/oatrice/Software-projects/Luma/luma_core/actions/quality_actions.py)

- **`sync_roadmap_for_closed_issues`**: 
    - When updating a table row, parse the existing status to see if it contains a version `(v...)` or note. If it does, and the new status matches the old status (or is just "Complete"), preserve the extra info.
    - When updating a list item, do the same for the "Status:" line.
    
- **`action_update_roadmap`**:
    - In `_build_status_strings`, if `version` or `note` are empty, check the existing content (if any) and carry over any version/note info found there.

## Verification Plan

### Automated Tests
- Create `tests/test_fix_roadmap_version_preservation.py` with the following test cases:
    1. `test_sync_roadmap_preserves_version_in_table`: Verify that `sync_roadmap_for_closed_issues` keeps `(v0.5.0)` when updating a table row.
    2. `test_sync_roadmap_preserves_version_in_list`: Verify that `sync_roadmap_for_closed_issues` keeps `(v0.5.0)` when updating a list item.
    3. `test_action_update_roadmap_preserves_version`: (Maybe harder to test due to input, but I can mock the input).

### Manual Verification
- Run `Luma` in the `JarWise` project.
- Manually trigger a roadmap update for an issue that already has a version in `ROADMAP.md`.
- Leave the version/note fields empty and verify that the existing `(v0.5.0)` is preserved.
