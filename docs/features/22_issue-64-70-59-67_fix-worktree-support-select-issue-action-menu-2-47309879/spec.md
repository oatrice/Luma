# Specification: Enhanced Git Worktree Support for Issue Selection and Code Review

> **Status**: Proposed
> **Owner**: AI Agent
> **Dates**: Created: 2026-04-10 | Last Updated: 2026-04-10

## 1. Context & Goal
*Why are we building this? What is the problem statement?*

### Problem
The current implementation of Luma CLI exhibits critical limitations when operating within a Git worktree environment. Specifically, the `[2] 📥 Select Issue (from Kanban)` action and the Code Review process (`action_code_review`) fail to correctly identify and utilize the active worktree's path.

For issue selection, Git operations (like branch creation and checkout) are incorrectly performed on the main repository, and generated files (`spec.md`, `plan.md`, `sbe.md`) are saved in the main repository's `docs/features/` directory instead of the worktree's.

For code review, the `get_git_changed_files()` function and other related utilities default to the main repository's path (`os.getcwd()` during module import), preventing the code review from detecting actual changes within the worktree. Consequently, `code_review.md` and `draft_code_review.md` are also saved in the wrong location. This behavior severely disrupts parallel development workflows that rely on Git worktrees for isolated feature development and review.

### Goal
To ensure Luma CLI provides full and consistent support for Git worktrees across all relevant actions, specifically the issue selection and code review workflows. This involves consistently resolving and utilizing the active worktree's path for all Git operations, file generations, and content analysis, thereby enabling seamless parallel development without interference with the main repository.

---

## 2. User Journey & Requirements
*What should the user experience?*

### User Story
As a **developer leveraging Git worktrees for parallel feature development**, I want Luma CLI to **recognize and operate exclusively within my active worktree** for actions such as issue selection, branch management, file generation, and code review, so that **my development environment remains isolated, and all Luma-generated artifacts are correctly associated with my worktree-specific changes**.

### Functional Requirements
- [x] The `_start_issues()` function (used by `[2] 📥 Select Issue (from Kanban)`) MUST consistently use the active worktree's path for all Git operations (e.g., branch creation, checkout).
- [x] The `_start_issues_headless()` function MUST consistently use the active worktree's path for all Git operations.
- [x] All file generation actions (e.g., `spec.md`, `plan.md`, `sbe.md`) invoked by issue selection MUST save files into the `docs/features/` directory relative to the active worktree's root.
- [x] Functions within `luma_core/tools.py` that perform Git operations or file path resolution (e.g., `get_git_changed_files()`, `suggest_version_from_git()`, `generate_branch_suggestions()`) MUST accept and correctly utilize an explicit `target_dir` parameter, defaulting to the active worktree's path if available.
- [x] The `action_code_review()` function and its downstream dependencies MUST correctly identify and analyze changes within the active worktree, rather than the main repository.
- [x] Generated code review documents (`code_review.md`, `draft_code_review.md`) MUST be saved within the `docs/features/` directory relative to the active worktree's root.
- [x] The `DEFAULT_TARGET_DIR` definition in `luma_core/config.py` MUST be made dynamic or eliminated in favor of explicit path passing or a robust context-aware path resolution mechanism.
- [x] Luma CLI MUST continue to function correctly for projects not utilizing Git worktrees (regression).

### Non-Functional Requirements
- [ ] **Consistency**: Luma's behavior and output MUST be identical whether run from a main repository or a worktree, given the same operational context.
- [ ] **Performance**: The changes MUST NOT introduce significant performance overhead during path resolution or Git operations.
- [ ] **Maintainability**: The solution MUST integrate cleanly with existing architecture, preferably by extending current path resolution utilities (e.g., `resolve_project_target_dir()`).

---

## 3. Specification by Example (SBE)
*Concrete examples of behavior.*

### Scenario: Selecting an Issue from a Worktree
**Given** a developer is in an active Git worktree `~/repo/worktrees/feature-x`
**And** Luma CLI is launched from within this worktree
**When** the user selects `[2] 📥 Select Issue (from Kanban)` and chooses an issue (e.g., `Issue #123`)
**Then** Luma CLI performs all Git operations (e.g., `git checkout -b feature-123`) within `~/repo/worktrees/feature-x`
**And** `spec.md`, `plan.md`, and `sbe.md` are generated in `~/repo/worktrees/feature-x/docs/features/issue-123/`

#### Examples
| Action | Current Directory | Expected Git Command Execution Path | Expected File Generation Path |
|---|---|---|---|
| Select Issue #123 | `~/repo/worktrees/feature-x` | `~/repo/worktrees/feature-x` | `~/repo/worktrees/feature-x/docs/features/issue-123/` |
| Select Issue #123 | `~/repo/main` | `~/repo/main` | `~/repo/main/docs/features/issue-123/` |

### Scenario: Performing Code Review in a Worktree
**Given** a developer is in an active Git worktree `~/repo/worktrees/bug-fix`
**And** Luma CLI is launched from within this worktree
**And** changes have been made and staged in `~/repo/worktrees/bug-fix`
**When** the user initiates a Code Review action
**Then** Luma CLI's code review process (e.g., `get_git_changed_files()`) identifies changes specifically within `~/repo/worktrees/bug-fix`
**And** `code_review.md` and `draft_code_review.md` are generated and saved in `~/repo/worktrees/bug-fix/docs/features/bug-fix-branch/` (or similar feature directory).

#### Examples
| Action | Current Directory | Expected `get_git_changed_files()` `target_dir` | Expected Code Review Document Save Path |
|---|---|---|---|
| Code Review | `~/repo/worktrees/bug-fix` | `~/repo/worktrees/bug-fix` | `~/repo/worktrees/bug-fix/docs/features/bug-fix-branch/` |
| Code Review | `~/repo/main` | `~/repo/main` | `~/repo/main/docs/features/main-branch/` |

---

## 4. Constraints & Risks
- **Constraint**: Must maintain backward compatibility with existing Luma CLI installations that do not use Git worktrees.
- **Risk**: Incorrect implementation of path resolution could lead to unintended Git operations on the wrong repository, potentially corrupting work or causing data loss.
- **Risk**: Over-reliance on `os.getcwd()` or module-level `DEFAULT_TARGET_DIR` could reintroduce the problem in future features or refactors. A robust, context-aware path resolution mechanism is crucial.
- **Risk**: Changes to `luma_core/tools.py` could have widespread, unforeseen impacts due to its utility nature. Thorough testing is required.
```