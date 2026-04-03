# Specification: Guided Planning Reliability for Multi-Issue Runs

> **Status**: Draft
> **Owner**: AI Product Manager
> **Dates**: Created: 2026-04-03 | Last Updated: 2026-04-03

## 1. Context & Goal
*Why are we building this? What is the problem statement?*

### Problem
Guided Planning can fail during a multi-issue run for two independent reasons.

The first failure occurs when the planning workspace name is derived directly from a combined multi-issue title and becomes longer than the supported filesystem basename limit. This can stop planning before artifacts are created.

The second failure occurs when the saved active LLM fallback position causes planning to retry only the tail of the configured model list instead of the full configured chain. If the saved model fails transiently, the workflow can stop even though earlier configured models are still available.

These failures break the expected `Analyst -> Spec -> SBE -> Architect` handoff, force manual recovery, and reduce confidence in Luma as the planning orchestrator for Zenith-driven workflows. This is especially visible in multi-issue runs such as `#13-14-15-8`, where the combined title is much longer than a normal single-issue title.

### Goal
Ensure Guided Planning remains reliable for multi-issue workflows by:

- always creating or reusing a safe planning workspace for long combined titles
- preserving combined-issue traceability without allowing path-length failures
- trying the full configured LLM fallback chain in circular order, beginning from the saved active position
- allowing planning to continue automatically whenever at least one configured model can still complete the current phase
- reducing manual recovery during Zenith-to-Luma planning handoff

### Affected Domains
- `Luma`: Guided Planning workflow, planning artifact continuity, fallback behavior, and operator trust.
- `Zenith`: Upstream multi-issue workflow that depends on uninterrupted planning and complete downstream artifacts.

---

## 2. User Journey & Requirements
*What should the user experience?*

### User Story
As a **workflow operator using Luma for Zenith multi-issue planning**, I want to **run Guided Planning reliably even when combined issue titles are very long or the current LLM fails transiently**, so that **I receive a complete planning artifact set without manual recovery**.

### User Journey
1. The operator selects multiple related issues and starts Guided Planning.
2. Luma creates or resolves a planning workspace for the combined task.
3. Analyst generates analysis output, then Spec, SBE, and Architect continue in sequence.
4. If the currently active model fails, Luma automatically tries the rest of the configured fallback chain instead of stopping early.
5. The operator either receives the expected planning artifacts or a final failure only after all configured recovery options are exhausted.

### Functional Requirements
- [ ] The system must create or resolve a planning workspace for combined multi-issue runs without failing because the derived folder basename is too long.
- [ ] The planning workspace name must remain deterministic for the same combined issue set and combined title so that successive phases reuse the same workspace.
- [ ] The planning workspace must preserve human traceability to the combined issue number even when the descriptive portion is shortened.
- [ ] Analyst and Spec must behave consistently when creating or locating planning artifacts for the same multi-issue run.
- [ ] The system must not create separate planning workspaces for the same run merely because different phases derive the name differently.
- [ ] Guided Planning must continue from Analyst through Spec, SBE, and Architect when a safe workspace can be created and at least one configured model succeeds.
- [ ] When a saved active fallback position exists, the fallback chain must start there and then continue through the remaining configured models in circular order until one succeeds or the chain is exhausted.
- [ ] If a later model succeeds, the workflow must continue normally and treat that successful model as the active fallback position for subsequent runs.
- [ ] A final planning failure must only be surfaced after every configured model has been attempted once for the current request.
- [ ] Automated regression coverage must protect both long-title multi-issue planning behavior and circular fallback recovery behavior.

### Non-Functional Requirements
- [ ] Reliability: Planning must not fail solely because of path-length overflow or a transient failure at the saved active model position.
- [ ] Compatibility: Existing single-issue runs and short, readable workspace names must continue to behave as before unless shortening is necessary for safety.
- [ ] Performance: Workspace naming and fallback ordering must add negligible local overhead relative to normal LLM response time.
- [ ] Security: Combined titles and saved fallback state must be treated as untrusted input; invalid names or invalid saved positions must not create unsafe paths or crash the workflow.
- [ ] Observability: The workflow must preserve clear visibility into whether planning continued, which model succeeded, and when the full fallback chain was exhausted.

---

## 3. Specification by Example (SBE)
*Concrete examples of behavior.*

### Scenario: Long combined issue titles still produce a valid planning workspace
**Given** a multi-issue Guided Planning run has a very long combined title  
**When** the workflow begins Analyst or Spec artifact generation  
**Then** the workflow must use a safe, deterministic workspace name under `docs/features/`, keep the combined issue reference visible, and continue planning instead of failing with a filename-length error

#### Examples
| Input | Output | Notes |
|-------|--------|-------|
| Selected issues: `13-14-15-8`; Combined title: `Rotate auth keys, add approval gates, preserve audit trail, improve rollout controls, and coordinate post-cutover recovery across Zenith enterprise tenants`; Phase: `Analyst` | `analysis.md` is created in a safe folder such as `docs/features/15_issue-13-14-15-8_rotate-auth-keys-approval-gates-audit-trail-9a7c2f1b/` | The descriptive portion may be shortened, but the combined issue number remains visible. |
| Same selected issues and title; Phase: `Spec` | `spec.md` is written into the same safe folder already used by Analyst | Analyst and Spec must resolve the same planning workspace. |
| Selected issue: `35`; Title: `Fix sticky fallback` | A readable short folder is used without unnecessary shortening | Single-issue and short-title behavior remains compatible. |

### Scenario: Fallback resumes from the saved position and wraps to earlier models
**Given** a saved active fallback position points near the end of the configured model chain  
**When** the current phase hits a transient failure on that starting model  
**Then** Guided Planning must continue trying the remaining models in circular order, including earlier models in the list, until one succeeds or the chain is exhausted

#### Examples
| Input | Output | Notes |
|-------|--------|-------|
| Saved active position: `6`; Phase: `Spec`; Outcomes for this request: `6=timeout`, `7=rate-limited`, `0=success` | The phase completes on model `0`, planning continues, and the active fallback position becomes `0` | The chain wraps instead of stopping at the tail of the list. |
| Saved active position: `7`; Phase: `SBE`; Outcomes for this request: `7=transient error`, `0=transient error`, `1=success` | The phase completes on model `1` and the workflow continues without manual recovery | The saved position is the first attempt, not the only segment tried. |

### Scenario: Planning fails only after one full circular pass when all models are unavailable
**Given** every configured model fails for the current planning request  
**When** Guided Planning completes one full circular pass of the configured chain starting from the saved position  
**Then** the phase must end with a final failure, report that automatic recovery was exhausted, and stop further planning handoff

#### Examples
| Input | Output | Notes |
|-------|--------|-------|
| Saved active position: `5`; Phase: `Spec`; Outcomes: `5,6,7,0,1,2,3,4 = all fail` | Planning returns a final failure after all configured models were attempted once | Prevents premature failure while keeping failure honest when no recovery path exists. |
| Saved active position: `0`; Phase: `SBE`; Outcomes: `0,1,2,3,4,5,6,7 = all fail` | Planning fails after one complete pass and does not loop indefinitely | Recovery remains bounded and predictable. |

---

## 4. Constraints & Risks
*What should we watch out for?*

- Constraint: Multi-issue planning remains a single combined planning workspace; this specification does not change issue grouping strategy.
- Constraint: The planning workspace must continue to live under `docs/features/` and remain traceable to the combined issue identifier.
- Constraint: The saved active fallback position remains the preferred starting point for future requests.
- Constraint: This specification covers Planning-phase behavior only; it does not redefine coding, PR creation, or issue board transitions.
- Risk: Strong shortening of long combined titles can reduce readability if traceability to the combined issue number is not preserved.
- Risk: If all configured models are unavailable, planning will still fail after exhausting the full chain.
- Risk: If different planning phases do not resolve the same safe workspace name, artifacts may fragment across multiple folders.
- Risk: Downstream consumers may still perceive instability if they rely on raw title-derived names instead of stable artifact lookup behavior.