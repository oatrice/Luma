# Walkthrough: Resolve Issues #106, #107, #111

## Changes Made
1. **Fix Missing VS Code CLI Crash (#106, #107)**:
   - Modified `luma_core/tools.py` to catch `FileNotFoundError` when executing `code --diff`.
   - Instead of terminating the process, it now gracefully logs a warning.
   - Added `tests/test_tools_code_diff.py` to ensure Luma handles missing `code` CLI properly.

2. **Force Export MR Prompt & Fix MR URL Bug (#111)**:
   - Modified `workflow_actions.py` to include a new option `[f] Force Export Prompt Only` to the `Create PRs?` interactive prompt.
   - Updated the MR duplicate checking logic to fallback to `existing.get('url')`. This fixes the bug where GitLab MR URLs were reported as `None`.
   - Updated `action_create_pr` to pass the `force_export_only` flag down to the publisher agent state.
   - Modified `publisher.py` to check for `state.get("force_export_only")`. If enabled, the agent successfully saves the draft prompt and immediately returns `{"url": None}`, aborting the actual API call to create an MR.
   - Added `tests/test_pr_force_export.py` to ensure that `publisher_agent` properly respects the `force_export_only` flag and skips user interaction and API calls.

## Validation Results
- The unit test `tests/test_tools_code_diff.py` runs and passes successfully, confirming `code` CLI errors don't crash Luma.
- The unit test `tests/test_pr_force_export.py` runs and passes successfully, confirming MR API calls are skipped when forced export is requested.
- The `PR/MR already exists: None` bug is resolved because it now correctly falls back to using the `url` property from the GitLab client's response.
- Changes for #106, #107, and #111 are all committed and successfully verified.
