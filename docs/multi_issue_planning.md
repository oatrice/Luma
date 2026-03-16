# Multi-Issue Planning in Luma (Current Behavior + Trade-offs)

## Context
When you add Issue #2 to a session that already has Issue #1, Luma treats the session as a **single combined task** for the Planning Phase (Analyst -> Spec -> Architect).
This means planning artifacts are generated for a **combined issue number** (e.g., `1-2`) and **do not reuse** the existing docs for Issue #1.

## Current Behavior (as-is)
- Uses `state.active_issues` to build a combined task title/body.
- Creates or looks for a feature folder with the combined issue number (e.g., `issue-1-2`).
- If `issue-1-2` docs do not exist, it creates a **new** planning folder and writes:
  - `analysis.md`
  - `spec.md`
  - `sbe.md` (auto-generated after Spec)
  - `plan.md`
- Existing Issue #1 docs are **not reused** or merged automatically.

## Trade-offs

### Option A: Combined Planning (current behavior)
**Pros**
- Single coherent narrative for a tightly-coupled scope.
- One planning set, one PR, easy to close multiple issues together.
- Good when issues are truly inseparable or must ship together.

**Cons**
- Existing Issue #1 docs are ignored.
- Traceability by individual issue is reduced.
- Changes in Issue #2 can force rework of the combined plan.
- Risk of scope creep because docs become “one big feature.”

### Option B: Separate Issue2 Folder (per-issue planning)
**Pros**
- Clear traceability per issue.
- Reuses Issue #1 docs without overwriting.
- Easier to postpone, split PRs, or reprioritize.
- Lower risk of scope creep.

**Cons**
- Requires manual synthesis of a combined behavior if needed.
- Possible duplication across specs/plans.
- More coordination if changes overlap.

## Alternative Strategies (Hybrid)

### 1) Umbrella + Addenda
- Create a small “umbrella” combined doc (high-level intent).
- Keep per-issue specs/plans as detailed addenda.
- Best for large features that include several issue-sized deliverables.

### 2) Primary + Delta
- Use Issue #1 docs as the baseline.
- Issue #2 docs focus only on the delta changes.
- Minimizes duplication but requires discipline and clear boundaries.

### 3) Split Planning, Combine PR
- Keep planning per issue.
- Combine at coding/PR stage if needed.
- Best for parallel work with a single release window.

## Quick Decision Guide
- Choose **Combined Planning** if issues are inseparable and must ship together.
- Choose **Separate Issue2 Folder** if you want clarity, reuse Issue #1 docs, or maintain flexibility.
- Use a **Hybrid strategy** when you need both high-level cohesion and per-issue traceability.

## Implementation Notes (for Luma maintainers)
- Planning entry point: `action_guided_workflow()`
- Combination logic: `action_refine_issue()`, `action_generate_spec()`, `action_generate_sbe()`
- Feature directory lookup uses combined number (e.g., `1-2`).
