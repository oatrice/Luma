# Specification: Add Headless CLI Contract for External Callers

> **Status**: Draft
> **Owner**: TBD
> **Dates**: Created: April 2, 2026 | Last Updated: April 2, 2026

## 1. Context & Goal
*Why are we building this? What is the problem statement?*

### Problem
External systems, such as Zenith, require programmatic access to Luma's functionalities for automation. Currently, the Luma CLI (`main.py`) does not support the necessary headless arguments (`--auto`, `--action`, `--json`) required by wrappers like `LumaCLI.run_action()`, preventing reliable integration and automated workflows.

### Goal
To provide a stable, machine-readable headless CLI contract for Luma, enabling external callers to invoke specific actions, receive structured JSON output for both success and failure scenarios, and utilize consistent non-zero exit codes for programmatic error handling.

---

## 2. User Journey & Requirements
*What should the user experience?*

### User Story
As a **Developer integrating with Luma CLI or an external system like Zenith**, I want to **invoke Luma CLI actions programmatically using headless arguments and parse the structured output**, so that **Luma workflows can be automated, integrated into CI/CD pipelines, and made interoperable with other development tools.**

### Functional Requirements
- [x] The Luma CLI (`main.py`) must accept `--auto`, `--action <name>`, `--json`, and `--project <key>` arguments.
- [x] The `--action` argument's value must be mapped to specific, predefined internal Luma actions.
- [x] When the `--json` flag is provided, the CLI must output results in a machine-readable JSON format to standard output.
- [x] The JSON output must include a `status` field, which can be either `"success"` or `"error"`.
- [x] On successful execution, the JSON output must contain `action`, `project`, and `result` fields. The `result` field will contain the specific output of the action.
- [x] On failure, the JSON output must contain `action`, `project`, and an `error` field detailing the failure reason.
- [x] The CLI must exit with a non-zero status code when an error occurs during execution.
- [x] A clear documentation for this headless CLI contract (arguments, JSON schema, exit codes) must be created.

### Non-Functional Requirements
- [ ] **Performance**: JSON serialization and deserialization should be efficient.
- [ ] **Usability**: The contract should be intuitive for external developers to use.
- [ ] **Robustness**: The CLI should handle invalid inputs and internal errors gracefully, providing clear JSON error messages and appropriate exit codes.

---

## 3. Specification by Example (SBE)
*Concrete examples of behavior.*

### Scenario: Successful Execution of a Code Review Action
**Given** Luma CLI is installed and configured with necessary credentials.
**When** The CLI is invoked with `--auto`, `--action code_review`, `--json`, and a valid `--project` key.
**Then** The `code_review` action is performed, a JSON object indicating success is printed to stdout, and the CLI exits with code 0.

#### Examples
| Command | Expected Stdout JSON | Expected Exit Code |
|---|---|---|
| `python3 main.py --auto --action code_review --json --project 1` | `{"status":"success","action":"code_review","project":"1","result":{"summary": "Code looks good. No major issues found.","suggestions": []}}` | 0 |

### Scenario: Execution of a Non-Existent Action
**Given** Luma CLI is installed.
**When** The CLI is invoked with `--auto`, `--action non_existent_action`, `--json`, and a valid `--project` key.
**Then** An error message indicating the action is not found is printed in JSON format to stdout, and the CLI exits with a non-zero code.

#### Examples
| Command | Expected Stdout JSON | Expected Exit Code |
|---|---|---|
| `python3 main.py --auto --action non_existent_action --json --project 1` | `{"status":"error","action":"non_existent_action","project":"1","error":"Action 'non_existent_action' not found."}` | 1 |

### Scenario: Action Execution with Internal Error
**Given** Luma CLI is installed and configured.
**When** The CLI is invoked with `--auto`, `--action create_pr`, `--json`, and `--project 1`, but the `create_pr` action encounters an internal error (e.g., GitHub API failure).
**Then** A JSON object indicating an error is printed to stdout, detailing the failure, and the CLI exits with a non-zero code.

#### Examples
| Command | Expected Stdout JSON | Expected Exit Code |
|---|---|---|
| `python3 main.py --auto --action create_pr --json --project 1` | `{"status":"error","action":"create_pr","project":"1","error":"Failed to create PR: Repository is not clean. Please commit or stash changes."}` | 2 |

### Scenario: Invoking CLI with an Unrecognized Argument
**Given** Luma CLI is installed.
**When** The CLI is invoked with an unknown flag.
**Then** The CLI prints a usage error message to stderr and exits with a non-zero code.

#### Examples
| Command | Expected Stderr Output | Expected Exit Code |
|---|---|---|
| `python3 main.py --unknown-flag` | `usage: main.py [-h] [--project PROJECT] [--auto] [--action ACTION] [--json]` (or similar usage string) | 2 |

---

## 4. Constraints & Risks
*What should we watch out for?*
- **Constraint**: Mapping of `--action` values to internal Luma functions needs to be robust and extendable without breaking existing interactive modes.
- **Constraint**: The JSON schema for success and failure must be well-defined and versioned to ensure backward compatibility for external integrations.
- **Risk**: Ensuring that all potential error conditions within Luma's actions are correctly caught and translated into the defined JSON error format and exit codes.
- **Risk**: Potential for conflicts if new arguments are added in the future that clash with the new headless arguments.