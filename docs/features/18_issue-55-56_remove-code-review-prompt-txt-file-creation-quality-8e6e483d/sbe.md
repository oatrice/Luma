# SBE (Specification by Example) Template

> 📅 Created: 2026-04-09
> 🔗 Issue: https://github.com/oatrice/Luma/issues/55

---

## Feature: Workspace Cleanup and Worktree-Aware Path Resolution

To reduce workspace clutter and ensure correct file placement, Luma must stop generating temporary prompt files and correctly identify the active Git worktree path as the target directory for output files, overriding the default project path in the configuration when applicable.

### Scenario: Workspace Cleanup - Redundant File Removal

**Given** the "code-review" action is triggered for a project
**When** the draft code review generation completes
**Then** the "code_review.md" file is saved to the target directory
**And** the file "code_review_prompt.txt" is NOT created in the target directory

#### Examples

| Project Path | Action | Output File | Prompt File Created |
|--------------|--------|-------------|---------------------|
| `/Users/oatrice/Software-projects/Cerebro` | `code-review` | `code_review.md` | `No` |
| `/home/runner/work/Luma` | `code-review` | `code_review.md` | `No` |
| `/tmp/test-project` | `code-review` | `code_review.md` | `No` |

---

### Scenario: Worktree Path Resolution - Execution from Git Worktree

**Given** a project is configured with a base path in Luma config
**And** the current execution context is within a Git worktree of that project
**When** the system resolves the project target directory
**Then** the output files must be saved to the actual worktree root path instead of the base path

#### Examples

| Config Project Path | Current Working Directory (Worktree) | Resolved Target Dir | Output File Full Path |
|---------------------|--------------------------------------|---------------------|-----------------------|
| `/Users/oatrice/Cerebro` | `/Users/oatrice/Cerebro-worktrees/feat-4-5-3` | `/Users/oatrice/Cerebro-worktrees/feat-4-5-3` | `/Users/oatrice/Cerebro-worktrees/feat-4-5-3/code_review.md` |
| `/opt/projects/Luma` | `/opt/projects/Luma-worktrees/issue-56` | `/opt/projects/Luma-worktrees/issue-56` | `/opt/projects/Luma-worktrees/issue-56/code_review.md` |
| `/Users/dev/app` | `/Users/dev/app-worktrees/hotfix-login` | `/Users/dev/app-worktrees/hotfix-login` | `/Users/dev/app-worktrees/hotfix-login/code_review.md` |

---

### Scenario: Standard Path Resolution - Execution from Main Repository

**Given** a project is configured with a base path in Luma config
**And** the current execution context is NOT within a worktree (standard Git repository)
**When** the system resolves the project target directory
**Then** the output files must be saved to the standard project path from the configuration

#### Examples

| Config Project Path | Current Working Directory | Is Git Worktree | Final Target Dir |
|---------------------|---------------------------|-----------------|------------------|
| `/Users/oatrice/Cerebro` | `/Users/oatrice/Cerebro` | `No` | `/Users/oatrice/Cerebro` |
| `/home/user/Luma` | `/home/user/Luma` | `No` | `/home/user/Luma` |
| `/tmp/test-repo` | `/tmp/test-repo` | `No` | `/tmp/test-repo` |

---

## Notes

- The system must use `resolve_project_target_dir()` in `luma_core/actions/quality_actions.py` to ensure consistent path resolution logic across all tools.
- Verification of the Git worktree path should be performed using `get_git_worktree_path()` to distinguish between the main repository and linked worktrees.
- Removal of `code_review_prompt.txt` applies specifically to the `action_code_review` function in `quality_actions.py`.