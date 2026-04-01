# SBE (Specification by Example) Template

> 📅 Created: 2026-04-02
> 🔗 Issue: https://github.com/oatrice/Luma/issues/27

---

## Feature: Headless CLI Contract for External Callers

This feature enables the Luma CLI to be invoked programmatically by external tools and services using headless arguments (`--auto`, `--action`, `--json`, `--project`). It ensures machine-readable input and output, facilitating automation and integration.

---

### Scenario: Successful Action Execution via Headless CLI

**Given** the Luma CLI is updated to support headless arguments `--auto`, `--action`, `--json`, and `--project`
**When** the CLI is invoked with a valid `--action` and `--project`
**Then** the CLI executes the specified action and returns a JSON object with `status` "success", the executed `action`, and the `project` identifier.

#### Examples

| action          | project |
|-----------------|---------|
| code_review     | 1       |
| plan            | 2       |
| analyze_metrics | 3       |

---

### Scenario: Error Handling - Unrecognized Action

**Given** the Luma CLI is updated to support headless arguments `--auto`, `--action`, `--json`, and `--project`
**When** the CLI is invoked with a valid `--auto`, `--json`, and `--project` argument, but an unrecognized `--action` name
**Then** the CLI returns a JSON object with `status` "error", the specified `action`, an `error` message detailing the unrecognized action, and exits with a non-zero status code.

#### Examples

| action              | project |
|---------------------|---------|
| invalid_action      | 1       |
| another_bad_action  | 2       |
| non_existent_action | 3       |

---

### Scenario: Error Handling - Missing Required Argument (`--action`)

**Given** the Luma CLI is updated to support headless arguments `--auto`, `--action`, `--json`, and `--project`
**When** the CLI is invoked with `--auto` and `--json`, but without the required `--action` argument
**Then** the CLI returns a JSON object with `status` "error" and an `error` message indicating the missing `--action` argument, and exits with a non-zero status code.

#### Examples

| project |
|---------|
| 1       |
| 2       |
| 3       |

---

## Notes

- The `result` field in the success JSON will contain the specific output of the executed action.
- Error messages in JSON failure responses should be specific and actionable.
- Non-zero exit codes are expected for all error scenarios.