# Specification: CLI Contract: Metadata Endpoint and Headless JSON Output Guarantees

> **Status**: Draft
> **Owner**: AI Product Manager
> **Dates**: Created: 2026-04-02 | Last Updated: 2026-04-02

## 1. Context & Goal
*Why are we building this? What is the problem statement?*

### Problem
External systems integrating with Luma require a reliable and stable interface to determine compatibility and version information before executing Luma actions. Currently, Luma's headless mode may output diagnostic messages on stdout alongside JSON, corrupting the output and breaking automated parsing. Additionally, there is no standardized way to programmatically retrieve critical metadata such as Luma's version, git commit, supported contract version, and available actions, which is essential for preflight checks and ensuring compatibility.

### Goal
To enhance Luma's headless CLI capabilities by introducing a dedicated, stable, and machine-readable metadata endpoint and ensuring a clean, JSON-only stdout for all headless JSON output. This will enable external consumers to confidently integrate with Luma, perform preflight checks, and guarantee compatibility by programmatically accessing essential version and contract information.

---

## 2. User Journey & Requirements
*What should the user experience?*

### User Story
As a **external system integrator (e.g., Zenith CLI)**, I want to **query Luma's version, contract, and supported actions via a stable, machine-readable metadata endpoint in headless mode**, so that I can **ensure compatibility, validate Luma's revision before execution, and avoid parsing errors caused by mixed stdout/stderr output**.

### Functional Requirements
- [x] Implement a `--meta --json` command-line option for Luma.
- [x] When invoked with `--meta --json`, Luma must output a JSON object to stdout containing: `version`, `git_commit`, `dirty`, `contract_version`, `supported_actions`, `python_version`.
- [x] Ensure that when `--meta --json` is used, *only* the JSON payload is emitted to stdout. All diagnostic messages, warnings, and logs should be directed to stderr.
- [x] The JSON payload structure must remain stable across Luma releases unless a new `contract_version` is introduced.
- [x] Provide comprehensive test coverage for the metadata endpoint, including payload structure, data accuracy, and failure scenarios.
- [x] Document the metadata contract fields and the stdout/stderr behavior for external consumers.

### Non-Functional Requirements
- [x] **Stability**: The metadata contract must be stable and backward-compatible across releases.
- [x] **Performance**: Metadata retrieval should be near-instantaneous in headless mode to avoid delaying preflight checks.
- [x] **Reliability**: The command must consistently return accurate information and adhere to the specified output format and stream separation.

---

## 3. Specification by Example (SBE)
*Concrete examples of behavior.*

### Scenario: Retrieving Metadata for Version Compatibility Checks
**Given** Luma is installed and the Git repository is clean.
**When** the command `luma --meta --json` is executed in a headless environment.
**Then** Luma should output a JSON object to stdout containing the current version, git commit, 'false' for dirty status, contract version, list of supported actions, and Python version. Diagnostic messages should go to stderr.

#### Examples
| Command | Stdout (JSON) | Stderr | Notes |
|---|---|---|---|
| `luma --meta --json` | `{"version": "1.6.0", "git_commit": "abcdef1", "dirty": false, "contract_version": "v1", "supported_actions": ["analyze", "plan", "code", "review"], "python_version": "3.9.18"}` | `""` | Assumes a clean repo and specific versions. |

### Scenario: Handling Non-JSON Output and Ensuring Clean Stdout
**Given** Luma is installed and there are pending diagnostic messages or warnings.
**When** the command `luma --meta --json` is executed in a headless environment.
**Then** Luma should output *only* the JSON payload to stdout and route all diagnostic messages to stderr.

#### Examples
| Command | Stdout (JSON) | Stderr | Notes |
|---|---|---|---|
| `luma --meta --json` | `{"version": "1.6.0", "git_commit": "abcdef1", "dirty": false, "contract_version": "v1", "supported_actions": ["analyze", "plan", "code", "review"], "python_version": "3.9.18"}` | `An informational message about Git repo status.&#x0A;Warning: Some configurations may not be optimal.` | Diagnostic messages are correctly captured on stderr. |

### Scenario: Handling Non-Git Repository Installations
**Given** Luma is installed in an environment that is not a Git repository.
**When** the command `luma --meta --json` is executed.
**Then** Luma should output a JSON object to stdout where `git_commit` and `dirty` fields are null or clearly indicate they are not applicable, and the `contract_version` and `supported_actions` are still provided. Diagnostic messages should go to stderr.

#### Examples
| Command | Stdout (JSON) | Stderr | Notes |
|---|---|---|---|
| `luma --meta --json` | `{"version": "1.6.0", "git_commit": null, "dirty": null, "contract_version": "v1", "supported_actions": ["analyze", "plan", "code", "review"], "python_version": "3.9.18"}` | `Warning: Luma is not installed in a Git repository. Git-specific metadata will not be available.` | Git fields are null, and a warning is issued. |

---

## 4. Constraints & Risks
*What should we watch out for?*
- Constraint: The `--meta` flag must be implemented such that it can be combined with other potential future headless flags without conflict.
- Constraint: The `git_commit` and `dirty` fields are contingent on the Luma installation being within a Git repository. The implementation must gracefully handle cases where it is not, potentially by returning `null` or a specific indicator.
- Risk: Future changes to Luma's internal versioning scheme, action definitions, or the underlying contract structure could lead to breaking changes in the metadata payload if not managed with strict versioning (e.g., `contract_version`).
- Risk: External consumers' parsing mechanisms for stdout/stderr might vary. Clear documentation of the expected separation and content of each stream is critical.
- Risk: Ensuring absolute JSON-only output on stdout in all headless scenarios, especially during complex startup sequences or error conditions, requires thorough testing under realistic subprocess conditions.