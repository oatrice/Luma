# Walkthrough - Preserve Version in ROADMAP.md

I have updated the Luma CLI to prevent it from removing version information (e.g., `(v0.5.0)`) and completion notes when updating the `ROADMAP.md` file.

## Changes Made

### Luma Core Actions

#### [luma_core/actions/quality_actions.py](file:///Users/oatrice/Software-projects/Luma/luma_core/actions/quality_actions.py)

- **Added `_extract_version_and_note`**: A helper function that uses regular expressions to find version strings like `(v1.2.3)` and any additional notes in the existing status text.
- **Updated `sync_roadmap_for_closed_issues`**: When automatically syncing closed issues, it now checks the existing status in `ROADMAP.md`. If a version or note is found, it's appended to the new "✅ Complete" status.
- **Updated `action_update_roadmap`**: Modified the manual update flow to:
    1.  Capture the existing content before replacement.
    2.  If the user skips entering a new version or note (by pressing Enter), it automatically reuses the existing one.
    3.  Improved string formatting to ensure version strings are always wrapped in parentheses and properly spaced.

## Verification Results

### Automated Tests
I added a new test suite and ran regression tests to ensure no existing functionality was broken.

```bash
pytest tests/test_fix_roadmap_version_preservation.py \
       tests/test_sync_roadmap_for_closed_issues.py \
       tests/test_action_update_roadmap.py
```

**Results:**
- `test_sync_roadmap_preserves_version_in_table_row`: ✅ PASS
- `test_sync_roadmap_preserves_version_in_list_item`: ✅ PASS
- `test_action_update_roadmap_preserves_existing_version_when_skipping_input`: ✅ PASS
- All existing roadmap sync tests: ✅ PASS

### Manual Test Checklist
- [x] Table rows with `(vX.X.X)` are preserved.
- [x] List items with `(vX.X.X)` are preserved.
- [x] Manual update allows keeping old version by skipping input.

> [!TIP]
> From now on, when you update an issue in the roadmap using Luma and you don't want to change the version, just press **Enter** when prompted for the version/note, and it will keep the current one!
