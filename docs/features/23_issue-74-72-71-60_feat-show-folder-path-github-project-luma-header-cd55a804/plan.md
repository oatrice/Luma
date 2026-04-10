# Implementation Plan: Luma Header Enhancement & UX Improvements

> **Refers to**: [Spec Link](./spec.md)
> **Status**: Draft

## 1. Architecture & Design

### Component View
- **Modified Components**: 
  - `luma_core/ui.py` - Header display logic
  - `luma_core/tools.py` - Worktree detection utilities
  - `main.py` - MENU_ACTIONS ordering
  - `luma_core/actions/admin_actions.py` - AI Brain sync filtering
- **New Components**: None
- **Dependencies**: Git CLI for worktree detection

### Data Model Changes
```python
# No new models - using existing project config structure
# project['kanban_number'] already exists
# project['path'] already exists
```

---

## 2. Step-by-Step Implementation

### Step 1: Add Worktree Detection Utility
- **Docs**: Update tools.py docstrings
- **Code**: Add `get_main_repo_name_from_worktree()` to `luma_core/tools.py`
- **Tests**: Add unit tests for worktree detection in `tests/test_tools.py`

### Step 2: Update Header Display
- **Docs**: None required - self-documenting
- **Code**: Modify `display_header()` in `luma_core/ui.py` with lazy import
- **Tests**: Verify header output with mocked project data

### Step 3: Reorder Menu Actions
- **Docs**: None required
- **Code**: Move "A" key to top of MENU_ACTIONS dict in `main.py`
- **Tests**: Verify menu order in interactive mode

### Step 4: Implement AI Brain Sync Filtering
- **Docs**: Document filtering logic
- **Code**: Add issue filtering in `action_sync_ai_brain()` based on state.active_issues
- **Tests**: Test filtering with mock issues from different projects

### Step 5: Standardize Version Format
- **Docs**: Update CHANGELOG.md headers
- **Code**: Update VERSION file to 0.x.x format
- **Tests**: Verify version format in CI checks

---

## 3. Verification Plan

> [!IMPORTANT]
> **Android Build Policy**: N/A - This is a CLI tool, no Android build required.

### Automated Tests
- [ ] Unit Tests: `tests/test_tools.py` - worktree detection
- [ ] Unit Tests: `tests/test_ui.py` - header display (mocked)
- [ ] Integration Tests: Menu ordering verification

### Manual Verification
- [ ] Start Luma in worktree - verify "(worktree)" suffix appears
- [ ] Start Luma in regular repo - verify no suffix
- [ ] Check menu - verify "A" is in top 3 positions
- [ ] Run AI Brain sync - verify only relevant issues synced
