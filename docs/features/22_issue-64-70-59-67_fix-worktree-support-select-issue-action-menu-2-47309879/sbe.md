# SBE (Specification by Example) Template

> 📅 Created: 2026-04-10
> 🔗 Issue: https://github.com/oatrice/Luma/issues/64

---

## Feature: Worktree Path Resolution for Luma CLI Actions

This feature ensures that Luma CLI actions, specifically "Select Issue (from Kanban)" and "Code Review," correctly identify and operate within the context of a Git worktree. All Git operations (branch creation, checkout, identifying changed files) and file generation/saving (e.g., `spec.md`, `plan.md`, `sbe.md`, `code_review.md`) will respect the active worktree's path, preventing operations from erroneously targeting the main repository. This resolves issues where changes made within a worktree were not recognized by Luma or files were saved to incorrect locations.

### Scenario: Operations within a Git Worktree - Happy Path

**Given** A user is operating in a valid Git worktree, and Luma CLI is invoked for an action requiring path resolution.
**When** The user performs `Select Issue (from Kanban)` or initiates a `Code Review` via the CLI.
**Then**
*   All Git operations (e.g., branch creation, checkout, identifying changed files) are performed within the active worktree.
*   Generated specification files (`spec.md`, `plan.md`, `sbe.md`) are saved within the `docs/features/` directory of the active worktree.
*   Code review reports (`code_review.md`, `draft_code_review.md`) are generated and saved within the active worktree.

#### Examples

| Action                    | Current Directory             | Expected Git Operation Location | Expected Spec/Plan Save Location          | Expected Code Review Save Location |
|---------------------------|-------------------------------|---------------------------------|-------------------------------------------|------------------------------------|
| Select Issue              | `/path/to/main_repo/worktreeA` | `/path/to/main_repo/worktreeA`  | `/path/to/main_repo/worktreeA/docs/features/` | N/A                                |
| Code Review               | `/path/to/main_repo/worktreeB` | `/path/to/main_repo/worktreeB`  | N/A                                       | `/path/to/main_repo/worktreeB/`    |
| Select Issue (Headless)   | `/path/to/main_repo/worktreeC` | `/path/to/main_repo/worktreeC`  | `/path/to/main_repo/worktreeC/docs/features/` | N/A                                |
| Add Issue (to session)    | `/path/to/main_repo/worktreeD` | `/path/to/main_repo/worktreeD`  | `/path/to/main_repo/worktreeD/docs/features/` | N/A                                |

---

### Scenario: Operations within the Main Repository - Edge Case

**Given** A user is operating in the main Git repository (not a worktree), and Luma CLI is invoked for an action requiring path resolution.
**When** The user performs `Select Issue (from Kanban)` or initiates a `Code Review` via the CLI.
**Then**
*   All Git operations are performed within the main repository.
*   Generated specification files are saved within the `docs/features/` directory of the main repository.
*   Code review reports are generated and saved within the main repository.

#### Examples

| Action                    | Current Directory        | Expected Git Operation Location | Expected Spec/Plan Save Location          | Expected Code Review Save Location |
|---------------------------|--------------------------|---------------------------------|-------------------------------------------|------------------------------------|
| Select Issue              | `/path/to/main_repo`     | `/path/to/main_repo`            | `/path/to/main_repo/docs/features/`       | N/A                                |
| Code Review               | `/path/to/main_repo`     | `/path/to/main_repo`            | N/A                                       | `/path/to/main_repo/`              |
| Select Issue (Headless)   | `/path/to/main_repo`     | `/path/to/main_repo`            | `/path/to/main_repo/docs/features/`       | N/A                                |

---

### Scenario: Invoked in a Non-Git Directory - Error Handling

**Given** A user is operating in a directory that is not part of any Git repository (neither main nor worktree).
**When** The user attempts to perform `Select Issue (from Kanban)` or `Code Review`.
**Then**
*   Luma CLI displays an error message indicating that it must be run within a Git repository.
*   No Git operations are attempted.
*   No files are generated or saved.

#### Examples

| Current Directory    | Action                        | Expected Error Message                                  |
|----------------------|-------------------------------|---------------------------------------------------------|
| `/tmp/non_git_project` | Select Issue (from Kanban)    | "Luma CLI must be run within a Git repository."         |
| `/home/user/documents` | Code Review                   | "Luma CLI must be run within a Git repository."         |
| `/var/log`           | Add Issue (to session, headless)| "Luma CLI must be run within a Git repository."         |

---

## Notes

- The `resolve_project_target_dir()` function from `luma_core/tools.py` should be consistently applied across all affected functions (`_start_issues()`, `_start_issues_headless()`, and all downstream functions called by `action_code_review()` that perform Git operations or file I/O).
- The `DEFAULT_TARGET_DIR` in `luma_core/config.py` should either be removed, made dynamic, or its usage in `luma_core/tools.py` functions must be explicitly overridden by a context-aware `target_dir` parameter.
- Verification must include successful execution of `tests/test_worktree_path_resolution.py` and ensuring no regressions for operations performed in a standard (non-worktree) Git repository.