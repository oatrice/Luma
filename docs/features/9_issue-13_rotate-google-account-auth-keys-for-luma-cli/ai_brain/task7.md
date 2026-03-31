# Task: Replace Diff File with `code --diff` command

## Research & Planning
- [x] Understand the current diff logic in `luma_core/actions/metrics_actions.py`
- [x] Create implementation plan

## Implementation (TDD)
- [x] Create failing test for `code --diff` command
- [x] Update `action_generate_project_report` to use `subprocess.run(["code", "--diff", ...])`
- [x] Remove old diff file creation logic

## Verification
- [x] Run tests to ensure `code --diff` is called
- [x] Verify no `_diff.md` file is created
