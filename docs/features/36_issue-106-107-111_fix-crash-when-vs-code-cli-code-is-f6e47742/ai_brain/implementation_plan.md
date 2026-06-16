# Goal: Feature: Force export prompt file for MR title/description without creating MR

Currently, the Luma workflow automatically creates or skips MRs during the "Create Pull Request" phase. When an MR already exists, it skips but has a bug where it prints `PR/MR already exists: None` because the URL field from the GitLab API isn't correctly resolved. 

We will introduce a new option `[f] Force Export Prompt Only` that forces the system to generate and export the PR title/description prompt to `draft_pr_prompt.md` without making any GitLab/GitHub API calls to actually create the MR. We will also fix the `None` URL bug.

## User Review Required
No major architectural changes.

## Proposed Changes

### Luma Core: Workflow Actions

#### [MODIFY] [luma_core/actions/workflow_actions.py](file:///Users/oatrice/Software%20Project/Luma/luma_core/actions/workflow_actions.py)
- **Fix None URL bug:** In `action_create_pr`, when evaluating `pr_url`, add `.get('url')` as a fallback since the GitLab client returns `{"url": ...}` instead of `web_url`.
  ```python
  pr_url = existing.get('web_url') or existing.get('html_url') or existing.get('url')
  ```
- **Add Force Export Option:** In `action_guided_workflow`, update the input prompt:
  ```python
  choice = ui.safe_input("   Create PRs? [y] Yes (confirm each), [a] Yes to All (auto), [f] Force Export Prompt Only, [n] No: ").strip().lower()
  ```
- Handle the `f` choice by calling `action_create_pr(..., force_export_only=True)`.
- Update the `action_create_pr` signature to accept `force_export_only: bool = False`.
- In `action_create_pr`, skip the "Check for existing PR" step if `force_export_only` is true, ensuring it always reaches the publisher agent.
- Add `force_export_only` to the `pub_state` dictionary so the publisher agent knows to abort after exporting the prompt.

### Luma Core: Publisher Agent

#### [MODIFY] [luma_core/agents/publisher.py](file:///Users/oatrice/Software%20Project/Luma/luma_core/agents/publisher.py)
- After the draft prompt is saved to `draft_pr_prompt.md` (around line 315), check if `state.get("force_export_only")` is True.
- If True, print a message: `✅ Force Export Complete. Prompt saved to <path>` and `return {"url": None}` immediately, bypassing the MR creation logic and API calls.

## Verification Plan

### Automated Tests
- Run existing tests `pytest tests/` to ensure no regressions.
- (Optional) Write a test `tests/test_pr_force_export.py` to assert that `publisher_agent` exits early when `force_export_only` is true.

### Manual Verification
- Run Luma via `python main.py` or equivalent, proceed to Step 6.
- Check if the prompt reads `Create PRs? [y] Yes (confirm each), [a] Yes to All (auto), [f] Force Export Prompt Only, [n] No: `.
- Select `f` and verify that `draft_pr_prompt.md` is generated and the execution successfully skips making an MR API call.
