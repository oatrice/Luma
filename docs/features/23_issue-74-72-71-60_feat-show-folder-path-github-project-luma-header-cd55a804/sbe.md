# SBE (Specification by Example)

> 📅 Created: 2026-04-10
> 🔗 Issues: #74, #72, #71, #60

---

## Feature: Luma CLI Header Enhancement & UX Improvements

Multiple UX improvements to Luma CLI: enhanced header display, menu reorganization, AI Brain sync filtering, and version standardization.

### Scenario: Header Display with Folder Path - Happy Path

**Given** User starts Luma CLI in a project directory
**When** The header renders
**Then** Folder path and GitHub Project info are displayed

#### Examples

| Project Path | Kanban Number | Expected Output |
|--------------|---------------|-----------------|
| `/Users/dev/Projects/Luma` | 5 | `📁 Folder: ...rs/dev/Projects/Luma` `🐙 GH Proj: Project #5` |
| `/very/long/path/to/project` | 12 | `📁 Folder: ...o/project` `🐙 GH Proj: Project #12` |
| `/short/path` | None | `📁 Folder: /short/path` |

### Scenario: Worktree Detection - Edge Case

**Given** User is inside a Git worktree directory
**When** The project name is determined
**Then** Original repo name is shown with "(worktree)" suffix

#### Examples

| Current Path | Main Repo | Display Name |
|--------------|-----------|--------------|
| `/Luma-worktrees/feat-1` | `/Luma` | `📂 Project: Luma (worktree)` |
| `/Cerebro-worktrees/fix` | `/Cerebro` | `📂 Project: Cerebro (worktree)` |
| `/Regular/Repo` | `/Regular/Repo` | `📂 Project: Repo` |

### Scenario: Menu Position - Happy Path

**Given** User opens Luma interactive menu
**When** Menu options are displayed
**Then** "A Auto Full Workflow" appears in top positions

#### Examples

| Position | Option | Notes |
|----------|--------|-------|
| 0 | Exit | Keep as exit option |
| A | Auto Full Workflow | Move to position after Exit |
| 1 | View Kanban | Shift down |
| 2 | Select Issue | Shift down |

### Scenario: AI Brain Sync Filtering - Error Handling

**Given** AI Brain sync is triggered
**When** System determines which issues to sync
**Then** Only issues matching current project/repo context are synced

#### Examples

| Current Issue | Available Issues | Synced Issues |
|---------------|------------------|---------------|
| #74 Luma | #74, #60 Cerebro, #71 Luma | #74, #71 |
| #60 Cerebro | #74 Luma, #60 Cerebro, #71 Luma | #60 |
| #72 Luma | #74 Luma, #72 Luma, #71 Luma | #72, #74, #71 |

### Scenario: Version Format Standardization - Happy Path

**Given** Version files exist in various formats
**When** Update process runs
**Then** All versions converted to 0.x.x format

#### Examples

| Current Version | File | Updated Version |
|-----------------|------|-----------------|
| `1.6.0` | VERSION | `0.1.0` |
| `v2.0` | package.json | `0.2.0` |
| `1.0.0-alpha` | CHANGELOG.md | `0.1.0-alpha` |

### Scenario: Long Path Truncation - Boundary Condition

**Given** Project path exceeds 40 characters
**When** Folder path is displayed
**Then** Path is truncated with leading ellipsis

#### Examples

| Full Path | Displayed Path |
|-----------|----------------|
| `/Users/name/Projects/Work/Luma` | `/Users/name/Projects/Work/Luma` (no trunc) |
| `/very/long/path/to/the/project/directory` | `...to/the/project/directory` |
| `/a/b/c/d/e/f/g/h/i/j/k/l/m/n/o/p` | `.../l/m/n/o/p` |

---

## Notes

- Circular import between ui.py and tools.py must be resolved via lazy imports
- Worktree detection uses `git worktree list --porcelain`
- Menu reordering preserves all existing key bindings
