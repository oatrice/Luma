# Specification: Luma Header Enhancement & Menu Reorganization

> **Status**: Draft
> **Owner**: Luma AI Architect
> **Dates**: Created: 2026-04-10 | Last Updated: 2026-04-10

## 1. Context & Goal

### Problem

**Issue #74**: Users need more context about the project environment when starting Luma CLI, especially in worktree scenarios. Currently, only the project name is shown without indicating if it's a worktree or the actual folder path.

**Issue #72**: The "A - Auto Full Workflow" menu option is buried in position ~14, making it hard to access despite being one of the most frequently used features.

**Issue #71**: AI Brain sync pulls in unrelated issues, polluting the project context with artifacts from issues not relevant to current work.

**Issue #60**: Version references need to be standardized to pre-release 0.x.x format across the codebase.

### Goal

Improve user experience by:
1. Adding folder path and GitHub Project info to the header
2. Making frequently-used menu options easily accessible
3. Ensuring AI Brain sync only pulls relevant issues
4. Standardizing version format to pre-release

---

## 2. User Journey & Requirements

### User Story

As a **developer using Luma CLI**, I want to **see clear project context and access common actions quickly**, so that **I can work more efficiently without confusion about which environment I'm in**.

### Functional Requirements

- [ ] **FR1**: Header displays folder path (truncated if >40 chars)
- [ ] **FR2**: Header displays GitHub Project number when kanban_number is configured
- [ ] **FR3**: Worktree projects show original repo name with "(worktree)" indicator
- [ ] **FR4**: Menu option "A" appears in top 3 positions
- [ ] **FR5**: AI Brain sync filters issues by current project/repo context
- [ ] **FR6**: All version references use 0.x.x format

### Non-Functional Requirements

- [ ] **NFR1**: No breaking changes to existing menu functionality
- [ ] **NFR2**: Circular import issues avoided in implementation
- [ ] **NFR3**: Backward compatibility maintained for config formats

---

## 3. Specification by Example (SBE)

### Scenario: Header Display with Worktree

**Given** User is in a Git worktree directory `/Users/dev/Projects/Luma-worktrees/feature-1`
**When** User starts Luma CLI
**Then** Header shows:
```
📂 Project: Luma (worktree)
📁 Folder: ...ts/Luma-worktrees/feature-1
🐙 GH Proj: Project #5
```

#### Examples

| Project Type | Path | Display |
|--------------|------|---------|
| Regular repo | `/Users/dev/Projects/Luma` | `📂 Project: Luma` |
| Worktree | `/Users/dev/Projects/Luma-worktrees/feat` | `📂 Project: Luma (worktree)` |
| Long path | `/very/long/path/to/project/name` | `📁 Folder: ...o/project/name` |

### Scenario: Menu Option Position

**Given** User opens Luma interactive menu
**When** Menu renders
**Then** Option "A" Auto Full Workflow appears in top 3 positions

#### Examples

| Menu Position | Option | Expected |
|---------------|--------|----------|
| 1 | 0 Exit | ✅ Keep |
| 2 | A Auto Full Workflow | ✅ Move here |
| 3 | 1 View Kanban | ... |

### Scenario: AI Brain Sync Filtering

**Given** User has selected issue #74 for Luma project
**When** AI Brain sync runs
**Then** Only artifacts from issue #74 and related Luma issues are synced

#### Examples

| Issue | Related to Current? | Sync? |
|-------|---------------------|-------|
| #74 Luma header | ✅ Yes | ✅ Sync |
| #60 Cerebro version | ❌ No | ❌ Skip |
| #71 Luma sync fix | ✅ Yes | ✅ Sync |

---

## 4. Constraints & Risks

- **Constraint 1**: Must avoid circular imports (ui.py ↔ tools.py)
- **Constraint 2**: Must work with existing PROJECTS config structure
- **Risk 1**: Menu reordering might confuse existing users - mitigate by keeping key bindings same
- **Risk 2**: Worktree detection might fail in edge cases - fallback to original behavior
