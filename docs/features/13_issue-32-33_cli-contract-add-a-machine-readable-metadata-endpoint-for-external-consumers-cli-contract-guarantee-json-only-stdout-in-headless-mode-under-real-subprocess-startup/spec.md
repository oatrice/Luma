# Specification: CLI Contract: Metadata Endpoint and Headless JSON Output Guarantees

> **Status**: Implemented
> **Owner**: AI Product Manager
> **Dates**: Created: 2026-04-02 | Last Updated: 2026-04-02

## 1. Context & Goal

### Problem
External systems integrating with Luma require a reliable and stable interface to determine compatibility and version information before executing Luma actions. Previously, Luma's headless mode could emit diagnostic text on stdout alongside JSON, corrupting machine-readable output. There was also no standardized metadata endpoint for version, git revision, supported actions, and runtime compatibility checks.

### Goal
Provide a stable headless CLI contract that external consumers such as Zenith can trust for:

- preflight compatibility checks through `--meta --json`
- stable stdout parsing for headless `--json` mode
- explicit version/contract/action discovery before invoking actions

---

## 2. User Journey & Requirements

### User Story
As an **external system integrator (for example Zenith)**, I want to **query Luma's version, contract, and supported actions through a stable machine-readable metadata endpoint and rely on JSON-only stdout in headless mode**, so that I can **validate compatibility and safely parse subprocess output**.

### Functional Requirements
- [x] Implement a `--meta --json` mode for Luma.
- [x] Return a stable JSON envelope on stdout for metadata mode.
- [x] Include metadata fields: `version`, `git_commit`, `dirty`, `contract_version`, `supported_actions`, `python_version`.
- [x] Keep metadata mode machine-readable and reject invalid flag combinations such as `--meta` with `--action`.
- [x] Ensure headless `--json` mode uses stdout for machine-readable JSON only.
- [x] Route diagnostics, warnings, and startup noise to stderr.
- [x] Add regression coverage for real subprocess startup behavior.
- [x] Document the external CLI contract for consumers.

### Non-Functional Requirements
- [x] **Stability**: The payload shape must remain stable unless `contract_version` changes.
- [x] **Reliability**: Headless stdout must remain parseable under real subprocess execution.
- [x] **Compatibility**: Interactive mode must remain unaffected when headless flags are not used.

---

## 3. Specification by Example

### Scenario: Metadata preflight success
**Given** Luma is available in the repository root.
**When** the command `python3 main.py --meta --json` is executed.
**Then** stdout must contain a parseable JSON payload with metadata details and stderr may contain warnings without corrupting stdout.

#### Example

| Command | Stdout (JSON) | Notes |
|---|---|---|
| `python3 main.py --meta --json` | `{"status":"success","mode":"metadata","result":{"version":"1.6.0","git_commit":"7346548185cd82dd8bea308f65015a256bc50646","dirty":true,"contract_version":"2.0","supported_actions":["code_review"],"python_version":"3.9.6"}}` | `version` is resolved from `VERSION` first. |

### Scenario: Invalid metadata flag combination
**Given** an external caller mistakenly mixes metadata mode with action execution flags.
**When** the command `python3 main.py --meta --json --action code_review` is executed.
**Then** Luma must return a machine-readable JSON error payload and a non-zero exit code.

#### Example

| Command | Stdout (JSON) | Exit Code |
|---|---|---|
| `python3 main.py --meta --json --action code_review` | `{"status":"error","action":"code_review","project":"1","error":"--meta cannot be combined with --action or --auto."}` | `2` |

### Scenario: Headless action error under real subprocess startup
**Given** Luma is started as a real subprocess in headless JSON mode.
**When** the command `python3 main.py --auto --action invalid_action --json --project 12` is executed.
**Then** stdout must still contain parseable JSON only, even if stderr contains warnings or diagnostics.

#### Example

| Command | Stdout (JSON) | Exit Code |
|---|---|---|
| `python3 main.py --auto --action invalid_action --json --project 12` | `{"status":"error","action":"invalid_action","project":"12","error":"Action 'invalid_action' not found."}` | `1` |

### Scenario: Non-git fallback shape remains stable
**Given** Luma runs in an environment where git metadata cannot be resolved.
**When** metadata mode is executed.
**Then** the payload shape must remain stable and fallback values should be machine-readable.

#### Example

| Field | Fallback Value |
|---|---|
| `git_commit` | `"unknown"` |
| `dirty` | `false` |

---

## 4. Constraints & Risks

- Constraint: `--meta` currently requires `--json`.
- Constraint: `--meta` must not be combined with `--action` or `--auto`.
- Constraint: The current stable headless action list is limited to `["code_review"]`.
- Risk: Future action expansion requires deliberate updates to `SUPPORTED_HEADLESS_ACTIONS` and docs.
- Risk: Third-party warnings may still appear on stderr depending on the Python environment.
- Risk: If the metadata payload shape changes without a `contract_version` bump, external callers may break.
