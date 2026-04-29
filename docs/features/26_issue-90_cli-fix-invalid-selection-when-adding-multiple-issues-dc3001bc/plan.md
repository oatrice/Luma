# Implementation Plan: Fix Invalid Selection When Adding Multiple Issues

> **Refers to**: [Spec Link](./spec.md)

> **Status**: Approved

## 1. Architecture & Design

*High-level technical approach.*

### Component View

- **Modified Components**: `luma_core/actions/issue_actions.py` - `action_add_issue` function

- **New Components**: None

- **Dependencies**: Existing `KanbanCard`, `IssueData`, `safe_input` utilities

### Data Model Changes

No data model changes required. Uses existing `IssueData` and state management.

---

## 2. Step-by-Step Implementation

### Step 1: Update Input Parsing Logic

- **Docs**: Update prompt message to indicate multi-select support

- **Code**: Modify `action_add_issue` to parse comma-separated indices similar to `action_select_issue`

- **Tests**: Add test case for comma-separated input

### Step 2: Add Duplicate Prevention

- **Docs**: Document duplicate checking behavior

- **Code**: Check if issue already in active_issues before adding

- **Tests**: Verify duplicate handling in tests

### Step 3: Update Error Handling

- **Docs**: Specify error messages for invalid indices

- **Code**: Provide specific error messages for invalid indices

- **Tests**: Test invalid input scenarios

---

## 3. Verification Plan

*How will we verify success?*

### Automated Tests

- [x] Unit Tests: `tests/test_issue_actions.py` - `test_add_multiple_issues_comma_separated`

- [x] Integration Tests: Manual testing with CLI

### Manual Verification

- [x] Test comma-separated input "1,2,3" adds multiple issues

- [x] Test invalid indices show error messages

- [x] Test duplicate selection is prevented

- [x] Test single selection still works