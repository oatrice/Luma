# Implementation Plan: Enhanced Git Worktree Support for Issue Selection and Code Review

> **Refers to**: [Spec Link](./spec.md)
> **Status**: Draft

## 1. Architecture & Design
*High-level technical approach.*

The core problem stems from Luma CLI's reliance on `os.getcwd()` and a static `DEFAULT_TARGET_DIR` for Git operations and file generation, which is insufficient in a Git worktree environment. The proposed solution involves implementing a robust, context-aware mechanism to determine the active Git worktree's root path. This path will then be explicitly passed to all functions performing Git operations or file I/O, ensuring they operate within the correct repository context.

### Component View
-   **Modified Components**:
    -   `luma_core/tools.py`: To include a new worktree path resolution utility and to update existing Git-related functions to accept an explicit `target_dir`.
    -   `luma_core/actions/`: Specifically `_start_issues` (and `_start_issues_headless`) and `action_code_review`, to use the resolved worktree path for Git commands and artifact generation.
    -   `luma_core/config.py`: Review and potentially remove/dynamize `DEFAULT_TARGET_DIR` if it serves as a static source of truth for repository paths.
    -   `tests/`: Existing and new test files will be updated to cover worktree scenarios.
-   **New Components**:
    -   A new utility function in `luma_core/tools.py` (e.g., `get_active_repo_root`) to reliably identify the current Git repository root and, if applicable, the active worktree's root.
-   **Dependencies**:
    -   The existing Git command-line tool.
    -   Standard Python libraries (`os`, `subprocess`).

### Data Model Changes
No explicit data model changes are required. However, function signatures will be updated to include `target_dir` parameters.

```python
# Example of a function signature change in luma_core/tools.py
# Old:
# def get_git_changed_files(...)
#
# New:
# def get_git_changed_files(target_dir: Optional[str] = None, ...) -> List[str]:
#    """
#    Retrieves changed files relative to the target_dir's Git repository.
#    If target_dir is None, resolves to the active worktree or main repository.
#    """
```

---

## 2. Step-by-Step Implementation

### Step 1: Implement Robust Worktree Path Resolution Utility
-   **Goal**: Create a reliable, context-aware utility function that determines the active Git worktree's root path or the main repository root if not in a worktree.
-   **Files**: `luma_core/tools.py`
-   **Code**:
    -   Add a new function `get_active_repo_root(current_path: Optional[str] = None) -> str`.
        -   This function will use `git rev-parse --show-toplevel` to find the main Git repository root.
        -   It will then use `git worktree list --porcelain` to determine if the `current_path` (or `os.getcwd()` if `None`) is within an active Git worktree.
        -   It will return the root path of the *active Git repository context* (i.e., the worktree root if in a worktree, otherwise the main repo root).
-   **Tests**: Add comprehensive unit tests in `tests/test_tools.py` for `get_active_repo_root` to cover:
    -   Execution from a main repository root.
    -   Execution from a subdirectory within a main repository.
    -   Execution from a worktree root.
    -   Execution from a subdirectory within a worktree.
    -   Edge cases (e.g., not within a Git repository).

### Step 2: Parameterize Git and File I/O Functions in `luma_core/tools.py`
-   **Goal**: Modify existing Git-related functions in `luma_core/tools.py` to accept an explicit `target_dir` parameter, defaulting to the result of `get_active_repo_root()`.
-   **Files**: `luma_core/tools.py`
-   **Code**:
    -   Update function signatures for `get_git_changed_files`, `suggest_version_from_git`, `generate_branch_suggestions`, and any other functions performing Git operations or path resolution that currently use `os.getcwd()`.
    -   The `target_dir` parameter will be optional and default to `get_active_repo_root()`.
    -   All Git commands executed by these functions will use `subprocess.run(..., cwd=target_dir)`.
-   **Tests**: Update existing unit tests in `tests/test_tools.py` for the modified functions to ensure:
    -   Correct behavior when `target_dir` is explicitly provided (for both main repo and worktree paths).
    -   Correct default behavior when `target_dir` is `None` (resolving to the active worktree/main repo root).
    -   No regressions for existing non-worktree use cases.

### Step 3: Refactor `luma_core/config.py` Path Handling
-   **Goal**: Eliminate static reliance on `DEFAULT_TARGET_DIR` for operational paths, replacing it with dynamic, context-aware path resolution where appropriate.
-   **Files**: `luma_core/config.py` and potentially modules importing it directly for path definitions.
-   **Code**:
    -   Review `DEFAULT_TARGET_DIR`. If it is used to determine the root for Git operations or artifact storage, replace its usage with calls to `get_active_repo_root()` at the point of use, or ensure the path is passed dynamically.
    -   Consider if `DEFAULT_TARGET_DIR` can be removed or repurposed for truly static, non-operational configuration.
-   **Tests**: Verify that any configurations that previously relied on `DEFAULT_TARGET_DIR` now correctly resolve paths using `get_active_repo_root()` in integration tests covering those features.

### Step 4: Update Issue Selection Actions (`_start_issues`, `_start_issues_headless`)
-   **Goal**: Ensure issue selection actions perform Git operations and generate files within the active worktree.
-   **Files**: `luma_core/actions/issue_selection.py` (or `luma_core/actions.py` if not modularized)
-   **Code**:
    -   At the beginning of these functions, obtain the active repository root using `get_active_repo_root()`.
    -   Pass this resolved path as `target_dir` to all calls to Git utility functions (e.g., branch creation, checkout).
    -   Construct the file generation paths (for `spec.md`, `plan.md`, `sbe.md`) using `os.path.join(active_repo_root, "docs/features/", issue_specific_directory)`.
-   **Tests**: Add integration tests in `tests/test_action_issue_selection.py` to:
    -   Verify that new branches are created and checked out within the active worktree (when run from a worktree).
    -   Verify that `spec.md`, `plan.md`, `sbe.md` are correctly generated within the worktree's `docs/features/` directory.
    -   Confirm that functionality remains correct when run from the main repository (regression).

### Step 5: Update Code Review Action (`action_code_review`)
-   **Goal**: Ensure the code review process correctly identifies changes and saves artifacts within the active worktree.
-   **Files**: `luma_core/actions/code_review.py` (or `luma_core/actions.py` if not modularized)
-   **Code**:
    -   At the beginning of `action_code_review`, obtain the active repository root using `get_active_repo_root()`.
    -   Pass this resolved path as `target_dir` to `get_git_changed_files()` and any other Git-related functions used for change detection.
    -   Construct save paths for `code_review.md` and `draft_code_review.md` using `os.path.join(active_repo_root, "docs/features/", feature_branch_directory)`.
-   **Tests**: Add integration tests in `tests/test_action_code_review.py` to:
    -   Verify that `get_git_changed_files()` correctly reports changes specific to the active worktree.
    -   Verify that `code_review.md` and `draft_code_review.md` are generated and saved within the worktree's `docs/features/` directory.
    -   Confirm that functionality remains correct when run from the main repository (regression).

### Step 6: Comprehensive Regression Testing
-   **Goal**: Ensure backward compatibility and no regressions for non-worktree scenarios, as well as overall system stability.
-   **Files**: Review all affected test files and ensure adequate coverage.
-   **Code**:
    -   No direct code changes in production files in this step. This is a verification step.
    -   Ensure the full test suite covers both worktree and non-worktree environments for all affected features.
-   **Tests**: Execute the entire `tests/` suite after all changes are implemented.

---

## 3. Verification Plan
*How will we verify success?*

### Automated Tests
-   **Unit Tests**:
    -   `tests/test_tools.py`: Verify `get_active_repo_root` handles main repos, worktrees, and subdirectories correctly. Verify updated `luma_core/tools.py` functions use `target_dir` correctly.
-   **Integration Tests**:
    -   `tests/test_action_issue_selection.py`: Test `_start_issues` and `_start_issues_headless` to ensure Git operations (branch creation/checkout) and file generation (`spec.md`, `plan.md`, `sbe.md`) occur within the active worktree's `docs/features/` directory.
    -   `tests/test_action_code_review.py`: Test `action_code_review` to ensure `get_git_changed_files()` analyzes the active worktree's changes and `code_review.md`, `draft_code_review.md` are saved in the worktree's `docs/features/` directory.
-   **Regression Tests**: Ensure all existing tests pass after modifications to confirm backward compatibility for non-worktree scenarios.

### Manual Verification

-   **Test Setup**:
    1.  Ensure `gh` CLI is authenticated.
    2.  Create a fresh Git repository (e.g., `luma-test-repo`).
    3.  Initialize it as a Git repository and make an initial commit.
    4.  Create a Git worktree: `git worktree add ../luma-test-worktree main`.
    5.  Populate `luma-test-repo` with a `docs/features/` directory.

-   **Scenario 1: Selecting an Issue from a Worktree**
    1.  Navigate to the worktree: `cd ../luma-test-worktree`.
    2.  Run Luma CLI and select `[2] 📥 Select Issue (from Kanban)`.
    3.  Choose an existing issue from Kanban.
    4.  **Expected**:
        -   A new branch is created and checked out within `luma-test-worktree` (confirm with `git branch` in the worktree).
        -   `spec.md`, `plan.md`, `sbe.md` are generated within `luma-test-worktree/docs/features/<issue-branch-name>/`.
        -   Verify that no changes occurred in the `luma-test-repo` (main repository).

-   **Scenario 2: Performing Code Review in a Worktree**
    1.  In `luma-test-worktree`, make some changes to a file (e.g., `touch test_file.py`).
    2.  Stage the changes: `git add .`.
    3.  Run Luma CLI and initiate the Code Review action.
    4.  **Expected**:
        -   Luma CLI's code review process identifies only `test_file.py` as changed within the `luma-test-worktree`.
        -   `code_review.md` and `draft_code_review.md` are generated and saved within `luma-test-worktree/docs/features/<current-branch-name>/`.
        -   Verify that no changes were detected or artifacts generated in `luma-test-repo`.

-   **Scenario 3: Non-Worktree Functionality (Regression)**
    1.  Navigate back to the main repository: `cd ../luma-test-repo`.
    2.  Perform issue selection and code review actions similar to Scenarios 1 & 2.
    3.  **Expected**:
        -   All functionalities should work exactly as they did before, with files generated and Git operations performed correctly in the main repository.

-   **Consistency Check**: After performing actions in both worktree and main repository, compare the output and generated artifacts. They should be consistent given their respective contexts.
