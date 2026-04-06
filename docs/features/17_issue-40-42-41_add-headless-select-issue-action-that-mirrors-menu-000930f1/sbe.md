# SBE (Specification by Example) Template

> 📅 Created: 2026-04-06
> 🔗 Issue: https://github.com/oatrice/Luma/issues/40

---

## Feature: Headless Issue Management & Guided Workflow Orchestration

This feature expands Luma's headless CLI capabilities to include issue selection with automated branch bootstrapping, first-class GitHub issue creation, and machine-readable execution of the "Auto Full Workflow." This ensures full parity between interactive menu-driven usage and automated external callers.

### Scenario: Headless Issue Selection & Branch Bootstrap - Happy Path

**Given** A project with active Kanban issues and an authenticated git environment
**When** The user executes the headless `select-issue` action with a specific issue ID
**Then** Luma should synchronize roadmap context, create or switch to the appropriate feature branch, update the internal state to `coding` phase, and return a JSON payload.

#### Examples

| issue_id | issue_title                   | expected_branch                    | next_phase | status  |
|----------|-------------------------------|------------------------------------|------------|---------|
| 40       | Add headless select action    | feat/40-add-headless-select        | coding     | success |
| 42       | Promote issue creation        | feat/42-promote-issue-creation     | coding     | success |
| 41       | Machine readable workflow     | feat/41-machine-readable-workflow  | coding     | success |

---

### Scenario: First-Class GitHub Issue Creation - Happy Path

**Given** An authenticated GitHub session and a target repository
**When** The user creates a new issue via the interactive menu or headless action
**Then** A GitHub issue is created with mandatory metadata (e.g., `## Related` section) and the resulting issue URL/Number is returned.

#### Examples

| title                        | related_ref | labels           | expected_body_contains | output_format |
|------------------------------|-------------|------------------|------------------------|---------------|
| Implement sandbox logger     | #39         | enhancement, cli | ## Related             | JSON          |
| Fix race condition in state  | none        | bug              | ## Related             | JSON          |
| Add telemetry to headless    | https://... | telemetry        | ## Related             | JSON          |

---

### Scenario: Resumable Headless Full Workflow - Boundary Conditions

**Given** A previously initiated workflow that was interrupted or stopped at a checkpoint
**When** The `full-workflow` action is called with the `--resume` flag and a state file
**Then** Luma should bypass completed phases and resume from the next logical checkpoint, emitting structured status updates for each step.

#### Examples

| last_completed_phase | resume_checkpoint | expected_next_step | exit_condition |
|----------------------|-------------------|--------------------|----------------|
| planning             | docs/plan.md      | coding             | wait_for_input |
| coding               | .luma_state       | code_review        | auto_proceed   |
| code_review          | .luma_state       | pr_creation        | success        |

---

### Scenario: Headless Action Failure - Error Handling

**Given** A headless command execution
**When** An invalid input is provided (e.g., non-existent issue ID) or a network error occurs
**Then** Luma must return a JSON error object with an `error_type` and non-zero exit code, preserving the machine-readable contract.

#### Examples

| action       | input_id | error_trigger            | expected_error_type | exit_code |
|--------------|----------|--------------------------|---------------------|-----------|
| select-issue | 9999     | Issue ID not found       | NOT_FOUND           | 1         |
| create-issue | N/A      | Missing required title   | VALIDATION_ERROR    | 1         |
| select-issue | 40       | Git branch exists (dirty)| GIT_ERROR           | 1         |

---

## Notes

- All headless actions MUST output valid JSON to `stdout`.
- `stderr` should be used for logs and human-readable warnings to avoid polluting JSON parsing.
- The `## Related` section in issue creation is mandatory to maintain repository traceability.
- Branch naming conventions must strictly follow `feat/ISSUE_NUMBER-description` or `fix/ISSUE_NUMBER-description`.