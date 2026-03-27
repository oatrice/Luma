# Walkthrough: Replace Diff File with `code --diff` command

I have replaced the logic that generates a `_diff.md` file when a report is overwritten with a direct call to the `code --diff` command. This provides a better visual experience in VS Code.

## Changes Made

### [Luma Core Actions]
- **Modified**: [metrics_actions.py](file:///Users/oatrice/Software-projects/Luma/luma_core/actions/metrics_actions.py)
    - Added `import subprocess`.
    - Updated `action_generate_project_report` to call `subprocess.run(["code", "--diff", original_path, output_path])` when a previous report exists.
    - Removed `difflib` usage and `_diff.md` file creation.

## Verification Results

### Automated Tests
I created a new test file [test_action_generate_project_report_diff.py](file:///Users/oatrice/Software-projects/Luma/tests/test_action_generate_project_report_diff.py) to verify the change.

- **Red Phase**: Verified that the test failed when the command was not called.
- **Green Phase**: Verified that the test passed after implementing the `subprocess.run` call.
- **Cleanup**: Verified that no `_diff.md` file is created.

```bash
export PYTHONPATH=$PYTHONPATH:. && python3 tests/test_action_generate_project_report_diff.py
```
**Output:**
```
.
----------------------------------------------------------------------
Ran 1 test in 0.002s

OK
```

## Proof of Work
The following diff shows the changes in `metrics_actions.py`:

render_diffs(file:///Users/oatrice/Software-projects/Luma/luma_core/actions/metrics_actions.py)
