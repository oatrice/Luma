# Specification: Guided Planning Reliability and Compact Artifact Naming

> Status: Implemented
> Last Updated: 2026-04-03

## 1. Context

Guided Planning must stay reliable for multi-issue runs, even when:

- the combined issue title is very long
- the title contains Thai text
- the saved active LLM fallback index points to a model that fails transiently

This issue fixes both planning artifact naming and fallback traversal so that Zenith-driven planning can continue automatically whenever at least one configured model still succeeds.

## 2. Functional Requirements

- The planning workspace must keep the prefix format `N_issue-<issue-number>_`.
- The descriptive slug must be ASCII-only.
- Thai text in titles must be transliterated to Latin/ASCII before slug compaction.
- The descriptive slug must be compact by design, not only truncated after hitting the filesystem limit.
- The descriptive slug must be limited to at most 8 tokens and 64 bytes before the final directory name is assembled.
- When compaction changes the descriptive slug, the system must append an 8-character hash suffix to reduce collisions.
- The final directory name must still respect the 255-byte basename limit.
- `Analyst`, `Spec`, and `SBE` must resolve the same feature directory for the same issue number.
- LLM fallback must start from the saved fallback index for the current working directory.
- LLM fallback must try the remaining configured models in circular order.
- Each configured model must be tried at most once for a single request.
- The successful model index must be persisted back through config-based fallback state.

## 3. Behavioral Specification

### 3.1 Directory Naming

The system uses `build_feature_dirname(index, issue_number, title)` as the single naming authority.

Behavior:

1. Normalize the title.
2. Transliterate Thai characters to ASCII/Latin.
3. Normalize punctuation and spaces into slug tokens.
4. Drop low-value stopwords when compacting.
5. Keep only the first 8 meaningful tokens.
6. Limit the descriptive slug to 64 bytes.
7. Append an 8-character SHA1 suffix when the compact form differs from the normalized original.
8. Assemble `N_issue-<issue-number>_<slug>`.
9. If the final basename would still exceed 255 bytes, apply one last byte-safe truncation while preserving the hash suffix.

### 3.2 Directory Reuse

`Analyst`, `Spec`, and `SBE` first try to locate an existing directory containing `issue-<issue-number>`.

If one already exists:

- the phase reuses that directory
- no new sibling directory is created for the same issue number

If none exists:

- the phase creates a new directory using `build_feature_dirname(...)`

### 3.3 Fallback Traversal

`FallbackModel` uses `config.get_fallback_info(current_path)` to obtain the saved active index.

Behavior:

1. Start from the saved index when it is valid.
2. Build an ordered list of model indices from that position to the end of the list.
3. Wrap around to the beginning of the list and continue until the saved position has been covered.
4. Attempt each model once at most.
5. Save the index of the first successful model through `config.save_fallback_index(...)`.
6. Raise a final error only after one full circular pass fails.

## 4. Specification by Example

### Scenario: Long multi-issue title creates a compact safe directory

**Given** a multi-issue planning run with a very long combined title  
**When** Analyst creates the planning artifact directory  
**Then** the basename remains traceable to the issue number, stays within filesystem limits, and is compact enough to remain readable

#### Examples

| Input | Expected Output |
|-------|-----------------|
| Issue number `13-14-15-8`, long combined title | A dirname such as `9_issue-13-14-15-8_luma-integration-extract-machine-readable-json-mixed-st-978b51fc` |
| Same issue number and title during Spec | The same directory is reused |
| Same issue number and title during SBE | The same directory is reused |

### Scenario: Thai titles become ASCII slugs

**Given** a title with Thai text  
**When** the title is converted into the descriptive slug  
**Then** the slug is ASCII-only and remains deterministic

#### Examples

| Input | Expected Output |
|-------|-----------------|
| `ปรับปรุงการสร้างโฟลเดอร์สำหรับหลาย issue` | `prabprungkarsrangofledorsamhrabhlay-issue` |

### Scenario: Fallback wraps around after the saved index

**Given** a saved active fallback index near the end of the model list  
**When** the starting model fails transiently  
**Then** the system keeps trying earlier configured models after wrapping around

#### Examples

| Model count | Saved index | Success index | Expected traversal |
|------------|-------------|---------------|--------------------|
| `3` | `2` | `0` | `2 -> 0` |
| `4` | `3` | `1` | `3 -> 0 -> 1` |
| `1` | `0` | none | `0` then final failure |

## 5. Non-Goals

- This implementation does not add a new fallback position field to `LumaState`.
- This implementation does not change issue grouping strategy for Guided Planning.
- This implementation does not perform semantic machine translation of Thai titles into natural English phrases.
- This implementation does not guarantee planning success when every configured model fails in the same request.
