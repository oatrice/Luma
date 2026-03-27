# Goal: Replace Diff File with `code --diff` command

The current implementation of `action_generate_project_report` calculates a diff between the new report and the previous one (if any) and saves it to a file ending in `_diff.md`. The user wants to instead trigger a visual diff in VS Code using the `code --diff` command.

## Proposed Changes

### [Component: Luma Core Actions]
#### [MODIFY] [metrics_actions.py](file:///Users/oatrice/Software-projects/Luma/luma_core/actions/metrics_actions.py)
Update `action_generate_project_report` to:
- Detect if a previous report version exists.
- If it exists, call `subprocess.run(["code", "--diff", original_path, output_path])` instead of using `difflib` and writing to `_diff.md`.
- Ensure `subprocess` is imported.

## Verification Plan

### Automated Tests
- Create `tests/test_action_generate_project_report.py`.
- Mock `subprocess.run` to ensure it's called with `["code", "--diff", ...]` when a previous version exists.
- Mock `os.path.exists` to simulate both existence and non-existence of previous reports.
- Verify that `difflib` and file writing for `_diff.md` are no longer used.

### Manual Verification
- Run the Luma CLI, generate a report for a project where a report already exists, and observe if VS Code opens the diff.
