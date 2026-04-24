# Specification: CLI Contract: Stable headless project selection by repo, path, or slug

> **Status**: Proposed
> **Owner**: Luma AI Architect
> **Dates**: Created: 2026-04-24 | Last Updated: 2026-04-24

## 1. Context & Goal
*Why are we building this? What is the problem statement?*

### Problem
External callers currently rely on a numeric `--project` identifier whose meaning can drift across local setups. This has already produced a live downstream correctness problem where an intended Zenith-focused run could resolve to JarWise instead. In addition, Luma's machine-readable headless responses currently echo the requested `project` value without explicitly telling callers which project/path/repo was resolved and used at execution time.

### Goal
Provide a stable headless project-selection contract that allows callers to target Luma work by repo, path, slug, or an equivalent durable selector, while preserving compatibility with legacy numeric `--project`. The contract must also return the resolved target identity explicitly in machine-readable output so upstream callers can verify downstream routing before trusting the result.

---

## 2. User Journey & Requirements
*What should the user experience?*

### User Story
As an **external system integrator (for example Zenith or Cerebro)**, I want to **invoke Luma headless actions with a stable `--project` selector and receive an explicit `resolved_target` in the JSON response**, so that **I can route work to the correct repo consistently across environments and audit what Luma actually targeted**.

### Functional Requirements
- [ ] `--project` in headless mode must accept a stable selector such as repo, path, slug, or an equivalent durable identity in addition to the existing numeric key.
- [ ] Explicit `--project` values must take precedence over stored last-project mappings and cwd inference.
- [ ] If the selector maps uniquely to a local target, Luma must resolve it deterministically and run the requested headless action against that target.
- [ ] If the selector is ambiguous or cannot be resolved safely, Luma must return a machine-readable error and must not silently fall back to another project.
- [ ] Headless JSON responses must include a `resolved_target` object that makes the resolved repo/path/key/slug explicit.
- [ ] Existing headless actions, especially `bootstrap`, must use the same project-resolution rules.
- [ ] Legacy numeric `--project` usage must continue to work.

### Non-Functional Requirements
- [ ] **Stability**: The existing top-level JSON contract (`status`, `action`, `project`, `result`/`error`) should be preserved, with `resolved_target` added additively.
- [ ] **Determinism**: Selector precedence and normalization must not depend on local numeric ordering alone.
- [ ] **Safety**: Ambiguous selectors must fail explicitly rather than route to the wrong repo.
- [ ] **Scope Control**: `#84` is a standalone contract fix and does not batch observability work from `#43` or doc-quality validation from `#44`.

---

## 3. Specification by Example (SBE)
*Concrete examples of behavior.*

### Scenario: Stable selector resolves the intended target
**Given** the caller provides an explicit stable selector in `--project`.
**When** Luma can map that selector to a unique local target.
**Then** the requested action must run against that target and the response must include the resolved identity explicitly.

#### Examples
| Input | Output | Notes |
|-------|--------|-------|
| `--project repo:oatrice/Luma` | `resolved_target.repo = "oatrice/Luma"` | Repo selector maps to the canonical Luma project entry. |
| `--project path:/Users/oatrice/Software-projects/Cerebro` | `resolved_target.path = "/Users/oatrice/Software-projects/Cerebro"` | Path selector remains stable even if numeric keys drift. |
| `--project slug:zenith` | `resolved_target.slug = "zenith"` | Slug is acceptable only when it resolves uniquely. |

### Scenario: Explicit selector overrides fragile numeric context
**Given** a local environment where stored project mappings or current cwd would otherwise point elsewhere.
**When** the caller passes an explicit stable selector in `--project`.
**Then** Luma must use that explicit selector as the source of truth.

#### Examples
| Input | Output | Notes |
|-------|--------|-------|
| `cwd=/Users/oatrice/Software-projects/Luma-worktrees/luma1`, `stored=1`, `--project repo:oatrice/Zenith` | `resolved_target.repo = "oatrice/Zenith"` | Explicit repo beats stored JarWise key. |
| `cwd=/Users/oatrice/Software-projects/Luma-worktrees/luma1`, `stored=12`, `--project path:/Users/oatrice/Software-projects/Cerebro` | `resolved_target.repo = "oatrice/Cerebro"` | Explicit path beats current Luma cwd. |
| `cwd=/Users/oatrice/Software-projects/Luma-worktrees/luma1`, `stored=1`, `--project 12` | `resolved_target.project_key = "12"` | Legacy numeric path still works when explicitly requested. |

### Scenario: Ambiguous or invalid selector fails without silent fallback
**Given** the caller provides a selector that cannot be mapped safely.
**When** Luma cannot resolve a unique local target.
**Then** it must return a machine-readable error and not run the action against another project.

#### Examples
| Input | Output | Notes |
|-------|--------|-------|
| `--project repo:oatrice/Cerebro` | JSON error | Repo selector is ambiguous across multiple local Cerebro entries. |
| `--project repo:oatrice/UnknownRepo` | JSON error | Repo selector is not mapped to a known local target. |
| `--project path:/tmp/not-a-repo` | JSON error | Invalid path must not silently degrade to cwd or stored project. |

### Scenario: Bootstrap remains compatible with the new resolver
**Given** `bootstrap` already exists as a headless action.
**When** the caller uses either a legacy numeric selector or a stable selector.
**Then** `bootstrap` must preserve existing behavior while also returning the resolved target explicitly.

#### Examples
| Input | Output | Notes |
|-------|--------|-------|
| `--action bootstrap --issue 84 --project 12 --json` | success JSON with `resolved_target.project_key = "12"` | Legacy bootstrap path remains supported. |
| `--action bootstrap --issue 36 --project path:/Users/oatrice/Software-projects/Zenith --json` | success JSON with `resolved_target.repo = "oatrice/Zenith"` | Path-based bootstrap works without relying on numeric key. |
| `--action bootstrap --issue 36 --project repo:oatrice/Zenith --json` | success JSON with explicit `resolved_target` or JSON error if local mapping is missing | Repo selector behavior is explicit and auditable either way. |

---

## 4. Constraints & Risks
*What should we watch out for?*
- Constraint: The project may continue to use the existing `--project` flag as the contract surface; no additional flags are required by this spec if the behavior is satisfied.
- Constraint: `resolved_target` is required, but rich bootstrap-specific payload expansion is not required in `#84`.
- Constraint: `#84` is scoped to selector correctness and response clarity; `#43` and `#44` stay out of scope.
- Risk: Some consumers may assume `project` is numeric-only; they should migrate to `resolved_target` as the source of truth.
- Risk: Slug-based resolution can become ambiguous as the number of registered repos grows.
- Risk: Returning an absolute local path is useful for auditing but exposes environment-specific metadata; this must be documented clearly.
