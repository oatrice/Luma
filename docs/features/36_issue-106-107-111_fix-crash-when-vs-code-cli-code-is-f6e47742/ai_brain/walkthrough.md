# Walkthrough: Force Export MR Prompt (#111)

## Changes Made
1. **workflow_actions.py**: 
   - Added a new option `[f] Force Export Prompt Only` to the `Create PRs?` interactive prompt.
   - Updated the MR duplicate checking logic to fallback to `existing.get('url')`. This fixes the bug where GitLab MR URLs were reported as `None`.
   - Updated `action_create_pr` to pass the `force_export_only` flag down to the publisher agent state.
2. **publisher.py**:
   - Modified `publisher_agent` to check for `state.get("force_export_only")`.
   - If enabled, the agent successfully saves the draft prompt and immediately returns `{"url": None}`, aborting the actual API call to create an MR.
3. **Tests**:
   - Added `tests/test_pr_force_export.py` to ensure that `publisher_agent` properly respects the `force_export_only` flag and skips user interaction and API calls.

## Validation Results
- The unit test `tests/test_pr_force_export.py` runs and passes successfully.
- The `PR/MR already exists: None` bug is resolved because it now correctly falls back to using the `url` property from the GitLab client's response.
- All code has been committed to branch `feature/111-force-export-mr-prompt`.

> [!NOTE]
> คุณสามารถเปิด Merge Request ของ branch นี้และ merge ลง main เพื่อปิด Issue 111 ได้เลยครับ
